"Implements the Arbitrator class."

# Copyright (c) 2022 Bill Fisher
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

import finsy.switch as _sw  # break circular import
from finsy import pbuf
from finsy.grpcutil import GRPCStatusCode
from finsy.log import LOGGER
from finsy.p4client import P4ClientError, P4Status
from finsy.proto import U128, p4r

_NOT_ASSIGNED = -1


class Arbitrator:
    """Manages state used for client/role arbitration.

    TODO: Eventually, make an AbtractArbitrator base class to handle
    the client arbitration, so different algorithms can be plugged in.
    """

    initial_election_id: int
    election_id: int
    is_primary: bool = False
    primary_id: int = _NOT_ASSIGNED
    role: p4r.Role | None = None

    def __init__(self, initial_election_id: int):
        self.initial_election_id = initial_election_id
        self.election_id = initial_election_id

    async def handshake(self, switch: "_sw.Switch", *, conflict: bool = False):
        """Perform the P4Runtime client arbitration handshake."""

        assert not self.is_primary

        if conflict:
            # Current election_id conflicts with another connection, so start
            # the bidding at one less.
            self.election_id -= 1

        response = await self._arbitration_request(switch)
        status = P4Status.from_status(response.status)
        primary_id = U128.decode(response.election_id)

        while status.code == GRPCStatusCode.NOT_FOUND:
            self.election_id = primary_id

            response = await self._arbitration_request(switch)
            status = P4Status.from_status(response.status)
            primary_id = U128.decode(response.election_id)

        assert status.code in (GRPCStatusCode.OK, GRPCStatusCode.ALREADY_EXISTS)

        self.primary_id = primary_id
        self.is_primary = status.code == GRPCStatusCode.OK
        self._check_invariant()

    async def update(self, switch: "_sw.Switch", msg: p4r.MasterArbitrationUpdate):
        "Called with subsequent arbitration update responses."

        status_code = P4Status.from_status(msg.status).code
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

    def reset(self):
        "Called when client stream disconnects."

        self.election_id = self.initial_election_id
        self.is_primary = False
        self.primary_id = _NOT_ASSIGNED

    def complete_request(self, msg: pbuf.PBMessage):
        "Complete request with role/election_id information."

        if isinstance(msg, p4r.ReadRequest):
            if self.role is not None:
                msg.role = self.role.name

        elif isinstance(
            msg,
            (p4r.SetForwardingPipelineConfigRequest, p4r.WriteRequest),
        ):
            if self.role is not None:
                role_name = self.role.name
                if role_name:
                    msg.role = role_name
                else:
                    msg.role_id = self.role.id

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
        """
        assert switch._p4client is not None

        try:
            # TODO: Maybe put a timeout on this receive?
            response = await switch._p4client.receive()

        except P4ClientError as ex:
            if ex.status.is_election_id_used:
                return None
            raise

        if response.WhichOneof("update") != "arbitration":
            raise ValueError(f"Unexpected response: {response!r}")

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
            if self.election_id >= self.primary_id:
                raise RuntimeError(
                    f"backup invariant failed: election_id={self.election_id}, primary_id={self.primary_id}"
                )
