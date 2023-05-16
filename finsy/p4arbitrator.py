"Implements the Arbitrator class."

# Copyright (c) 2022-2023 Bill Fisher
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pyright: reportPrivateUsage=false

import finsy.switch as _sw  # break circular import
from finsy import pbuf
from finsy.grpcutil import GRPCStatusCode
from finsy.log import LOGGER
from finsy.p4client import P4ClientError, P4RpcStatus
from finsy.proto import U128, p4r

_NOT_ASSIGNED = -1


class Arbitrator:
    """Manages state used for client/role arbitration.

    TODO: Eventually, make an AbtractArbitrator base class to handle
    the client arbitration, so different algorithms can be plugged in.
    """

    initial_election_id: int
    election_id: int
    role: p4r.Role | None
    is_primary: bool = False
    primary_id: int = _NOT_ASSIGNED

    def __init__(
        self,
        initial_election_id: int,
        role_name: str = "",
        role_config: pbuf.PBMessage | None = None,
    ):
        self.initial_election_id = initial_election_id
        self.election_id = initial_election_id
        self.role = _create_role(role_name, role_config)

    @property
    def role_name(self) -> str:
        "Role name or '' if there is no role set."
        if self.role is None:
            return ""
        return self.role.name

    async def handshake(self, switch: "_sw.Switch", *, conflict: bool = False) -> None:
        """Perform the P4Runtime client arbitration handshake."""
        assert not self.is_primary

        if conflict:
            # Current election_id conflicts with another connection, so start
            # the bidding at one less.
            self.election_id -= 1

        response = await self._arbitration_request(switch)
        status = P4RpcStatus.from_status(response.status)
        primary_id = U128.decode(response.election_id)

        while status.code == GRPCStatusCode.NOT_FOUND:
            self.election_id = primary_id

            response = await self._arbitration_request(switch)
            status = P4RpcStatus.from_status(response.status)
            primary_id = U128.decode(response.election_id)

        assert status.code in (GRPCStatusCode.OK, GRPCStatusCode.ALREADY_EXISTS)

        self.primary_id = primary_id
        self.is_primary = status.code == GRPCStatusCode.OK
        self._check_invariant()

    async def update(
        self,
        switch: "_sw.Switch",
        msg: p4r.MasterArbitrationUpdate,
    ) -> None:
        "Called with subsequent arbitration update responses."
        status_code = P4RpcStatus.from_status(msg.status).code
        new_primary_id = U128.decode(msg.election_id)

        if new_primary_id >= self.primary_id:
            self.primary_id = new_primary_id
        else:
            # TECHDEBT: simple_switch_grpc sends a status code of OK and a
            # decreased election_id when it wants the next backup client to
            # become the primary.
            LOGGER.warning("election_id decreased to %r", new_primary_id)
            if (
                status_code == GRPCStatusCode.OK
                and not self.is_primary
                and new_primary_id == self.election_id
            ):
                status_code = GRPCStatusCode.NOT_FOUND

        match status_code:
            case GRPCStatusCode.OK:
                if not self.is_primary:
                    self.is_primary = True
                    switch._become_primary()
            case GRPCStatusCode.ALREADY_EXISTS:
                if self.is_primary:
                    self.is_primary = False
                    switch._become_backup()
            case GRPCStatusCode.NOT_FOUND:
                self.is_primary = False
                await self._request_primary(switch)
            case other:
                raise ValueError(f"Unexpected status: {other!r}")

    def reset(self) -> None:
        "Called when client stream disconnects."
        self.election_id = self.initial_election_id
        self.is_primary = False
        self.primary_id = _NOT_ASSIGNED

    def complete_request(self, msg: pbuf.PBMessage) -> None:
        "Complete request with role/election_id information."
        if isinstance(msg, p4r.ReadRequest):
            if self.role is not None:
                msg.role = self.role.name

        elif isinstance(
            msg,
            (p4r.SetForwardingPipelineConfigRequest, p4r.WriteRequest),
        ):
            if self.role is not None:
                msg.role = self.role.name

            msg.election_id.CopyFrom(U128.encode(self.election_id))

    async def _arbitration_request(self, switch: "_sw.Switch"):
        "Send a MasterArbitrationUpdate request and wait for the response."
        for _ in range(5):
            await self._send(switch)

            response = await self._receive(switch)
            if response is not None:
                return response

            self.election_id -= 1

        raise ValueError("no compatible election_id")

    async def _request_primary(self, switch: "_sw.Switch"):
        "Send a request to become the new primary."
        self.election_id = self.primary_id
        await self._send(switch)

    async def _send(self, switch: "_sw.Switch") -> None:
        "Send MasterArbitrationUpdate message to switch."
        assert self.election_id >= 0
        assert switch._p4client is not None

        request = p4r.StreamMessageRequest(
            arbitration=p4r.MasterArbitrationUpdate(
                role=self.role,
                device_id=switch.device_id,
                election_id=U128.encode(self.election_id),
            )
        )

        await switch._p4client.send(request)

    async def _receive(
        self,
        switch: "_sw.Switch",
    ) -> p4r.MasterArbitrationUpdate | None:
        """Wait for MasterArbitrationUpdate response from switch.

        Return None if the response indicates the `election_id` is in use.

        Log and ignore any other responses from the switch. Since this method
        can wait indefinitely, the caller should put a timeout on this method.
        """
        assert switch._p4client is not None

        try:
            while True:
                response = await switch._p4client.receive()
                if response.WhichOneof("update") == "arbitration":
                    break
                LOGGER.warning("Arbitrator ignored response: %r", response)

        except P4ClientError as ex:
            if ex.is_election_id_used:
                return None
            raise

        # TODO: Match arbitration response to request we sent?

        return response.arbitration

    def _check_invariant(self):
        "Check the Arbitrator's invariant."
        if self.is_primary:
            # When we're the primary, election_id must equal primary_id.
            if self.election_id != self.primary_id:
                raise RuntimeError(
                    f"primary invariant failed: election_id={self.election_id}, primary_id={self.primary_id}"
                )
        else:
            # When we're the backup, election_id must be less than primary_id.
            # FIXME: Unless we're renegotiating?
            if self.election_id >= self.primary_id:
                raise RuntimeError(
                    f"backup invariant failed: election_id={self.election_id}, primary_id={self.primary_id}"
                )


def _create_role(
    role_name: str,
    role_config: pbuf.PBMessage | None,
) -> p4r.Role | None:
    "Create a new P4Runtime Role object."
    if not role_name and role_config is None:
        return None

    if role_config is None:
        raise ValueError("role_config cannot be None when role_name is set")

    return p4r.Role(
        name=role_name,
        # [2021-10-18] If I remove the `pbuf.to_any()` and try
        # to set the message field `config=role_config`, I get a segmentation
        # fault on MacOS. [protobuf 4.21.7]
        config=pbuf.to_any(role_config),
    )
