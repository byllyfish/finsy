"Implements the Switch class."

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

import asyncio
import dataclasses
import enum
import logging
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from types import TracebackType
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Coroutine,
    Iterable,
    NamedTuple,
    SupportsBytes,
    TypeVar,
)

import grpc  # pyright: ignore[reportMissingTypeStubs]
import pyee
from typing_extensions import Self

from finsy import p4entity, pbuf
from finsy.futures import CountdownFuture
from finsy.gnmiclient import gNMIClient, gNMIClientError
from finsy.grpcutil import GRPCStatusCode
from finsy.log import LOGGER, TRACE
from finsy.p4arbitrator import Arbitrator
from finsy.p4client import P4Client, P4ClientError
from finsy.p4schema import P4ConfigAction, P4ConfigResponseType, P4Schema
from finsy.ports import PortList
from finsy.proto import p4r

# Maximum size of queues used for PacketIn, DigestList, etc.

_DEFAULT_QUEUE_SIZE = 50

# If switch fails to run for longer than _FAIL_MIN_TIME_SECS, wait
# _FAIL_THROTTLE_SECS before trying again.

_FAIL_MIN_TIME_SECS = 2.0
_FAIL_THROTTLE_SECS = 10.0

_T = TypeVar("_T")


@dataclasses.dataclass(frozen=True)
class SwitchOptions:
    """`SwitchOptions` manages the configuration options for a `Switch`.

    Each `SwitchOptions` object is immutable and may be shared by multiple
    switches. You should treat all values as read-only. You can use function call
    syntax to change one or more properties and construct a new object.

    ```
    opts = SwitchOptions(device_id=5)
    new_opts = opts(device_id=6)
    ```
    """

    p4info: Path | None = None
    "Path to P4Info protobuf text file."

    p4blob: Path | SupportsBytes | None = None
    "Path to P4Blob file, or an object that can provide the bytes value."

    device_id: int = 1
    "Default P4Runtime device ID."

    initial_election_id: int = 10
    "Initial P4Runtime election ID."

    channel_credentials: grpc.ChannelCredentials | None = None
    "P4Runtime channel credentials. Used for TLS support."

    ready_handler: Callable[["Switch"], Coroutine[Any, Any, None]] | None = None
    "Ready handler async function callback."

    config: Any = None
    "Store your app's configuration information here."

    def __call__(self, **kwds: Any):
        return dataclasses.replace(self, **kwds)


_SEMVER_REGEX = re.compile(r"^(\d+)\.(\d+)\.(\d+)(.*)$")


class ApiVersion(NamedTuple):
    "Represents the semantic version of an API."

    major: int
    minor: int
    patch: int
    extra: str  # optional pre-release/build info

    @classmethod
    def parse(cls, version_str: str) -> Self:
        "Parse the API version string."
        m = _SEMVER_REGEX.match(version_str)
        if not m:
            raise ValueError(f"unexpected version string: {version_str}")
        return cls(int(m[1]), int(m[2]), int(m[3]), m[4])

    def __str__(self) -> str:
        "Return the version string."
        return ".".join(map(str, self[:3])) + self.extra


class Switch:
    """`Switch` manages a P4Runtime Switch.

    A `Switch` is constructed with a `name`, `address` and an optional
    `SwitchOptions` configuration.
    """

    _name: str
    _address: str
    _options: SwitchOptions
    _p4client: P4Client | None
    _p4schema: P4Schema
    _tasks: "SwitchTasks | None"
    _queues: dict[str, asyncio.Queue[Any]]
    _packet_queues: list[tuple[Callable[[bytes], bool], asyncio.Queue[Any]]]
    _arbitrator: "Arbitrator"
    _gnmi_client: gNMIClient | None
    _ports: PortList
    _is_channel_up: bool = False
    _api_version: ApiVersion = ApiVersion(1, 0, 0, "")

    control_task: asyncio.Task[Any] | None = None
    "Used by Controller to track switch's main task."

    ee: "SwitchEmitter"
    "Event emitter."

    attachment: Any = None
    "Available to attach per-switch services or data."

    def __init__(
        self,
        name: str,
        address: str,
        options: SwitchOptions | None = None,
    ) -> None:
        if options is None:
            options = SwitchOptions()

        self._name = name
        self._address = address
        self._options = options
        self._p4client = None
        self._p4schema = P4Schema(options.p4info, options.p4blob)
        self._tasks = None
        self._queues = {}
        self._packet_queues = []
        self._arbitrator = Arbitrator(options.initial_election_id)
        self._gnmi_client = None
        self._ports = PortList()
        self.ee = SwitchEmitter(self)

    @property
    def name(self) -> str:
        "Name of the switch."
        return self._name

    @property
    def address(self) -> str:
        "Address of the switch."
        return self._address

    @property
    def options(self) -> SwitchOptions:
        "Switch options."
        return self._options

    @options.setter
    def options(self, opts: SwitchOptions):
        "Set switch options to a new value."
        if self._p4client is not None:
            raise RuntimeError("Cannot change switch options while client is open.")

        self._options = opts
        self._p4schema = P4Schema(opts.p4info, opts.p4blob)
        self._arbitrator = Arbitrator(opts.initial_election_id)

    @property
    def device_id(self) -> int:
        "Switch's device ID."
        return self._options.device_id

    @property
    def is_up(self) -> bool:
        "True if switch is UP."
        return self._is_channel_up

    @property
    def is_primary(self) -> bool:
        "True if switch is primary."
        return self._arbitrator.is_primary

    @property
    def primary_id(self) -> int:
        "Election ID of switch that is currently primary."
        return self._arbitrator.primary_id

    @property
    def election_id(self) -> int:
        "Switch's current election ID."
        return self._arbitrator.election_id

    @property
    def p4info(self) -> P4Schema:
        "Switch's P4 schema."
        return self._p4schema

    @property
    def gnmi_client(self) -> gNMIClient | None:
        "Switch's gNMI client."
        return self._gnmi_client

    @property
    def ports(self) -> PortList:
        "Switch's list of interfaces."
        return self._ports

    @property
    def api_version(self) -> ApiVersion:
        "P4Runtime protocol version."
        return self._api_version

    async def read_packets(
        self,
        *,
        queue_size: int = _DEFAULT_QUEUE_SIZE,
        eth_types: Iterable[int] | None = None,
    ) -> AsyncIterator["p4entity.P4PacketIn"]:
        "Async iterator for incoming packets (P4PacketIn)."

        if eth_types is None:

            def _pkt_filter(payload: bytes) -> bool:
                return True

        else:
            _filter = {eth.to_bytes(2, "big") for eth in eth_types}

            def _pkt_filter(payload: bytes) -> bool:
                return payload[12:14] in _filter

        LOGGER.debug("read_packets: opening packet queue: eth_types=%r", eth_types)

        queue = asyncio.Queue[Any](queue_size)
        queue_filter = (_pkt_filter, queue)
        self._packet_queues.append(queue_filter)

        try:
            while True:
                result = await queue.get()
                yield result

        finally:
            LOGGER.debug("read_packets: closing packet queue: eth_types=%r", eth_types)
            self._packet_queues.remove(queue_filter)

    def read_digests(
        self,
        *,
        queue_size: int = _DEFAULT_QUEUE_SIZE,
    ) -> AsyncIterator["p4entity.P4DigestList"]:
        "Async iterator for incoming digest lists (P4DigestList)."
        return self._queue_iter("digest", queue_size)

    def read_idle_timeouts(
        self,
        *,
        queue_size: int = _DEFAULT_QUEUE_SIZE,
    ) -> AsyncIterator["p4entity.P4IdleTimeoutNotification"]:
        "Async iterator for incoming idle timeouts (P4IdleTimeoutNotification)."
        return self._queue_iter("idle_timeout_notification", queue_size)

    async def _queue_iter(self, name: str, size: int) -> AsyncIterator[Any]:
        "Helper function to iterate over a Packet/Digest queue."
        assert name != "arbitration"

        if name in self._queues:
            raise RuntimeError(f"iterator {name!r} already open")

        LOGGER.debug("_queue_iter: opening queue %r", name)
        queue = asyncio.Queue[Any](size)
        self._queues[name] = queue

        try:
            while True:
                result = await queue.get()
                yield result
        finally:
            LOGGER.debug("_queue_iter: closing queue %r", name)
            del self._queues[name]

    @TRACE
    async def run(self):
        "Run the switch's lifecycle repeatedly."
        assert self._p4client is None
        assert self._tasks is None

        self._tasks = SwitchTasks()
        self._p4client = P4Client(self._address, self._options.channel_credentials)
        self._switch_start()

        try:
            while True:
                # If the switch fails and restarts too quickly, slow it down.
                async with _throttle_failure():
                    self.create_task(self._run(), background=True)
                    await self._tasks.wait()
                    self._arbitrator.reset()

        finally:
            self._p4client = None
            self._tasks = None
            self._switch_stop()

    def create_task(
        self,
        coro: Coroutine[Any, Any, _T],
        *,
        background: bool = False,
        name: str | None = None,
    ) -> asyncio.Task[_T]:
        "Create an asyncio task tied to the Switch's lifecycle."
        assert self._tasks is not None

        return self._tasks.create_task(
            coro,
            switch=self,
            background=background,
            name=name,
        )

    @TRACE
    async def _run(self):
        "Main Switch task runs the stream."
        assert not self._is_channel_up
        assert self._p4client is not None

        try:
            await self._p4client.open(
                schema=self.p4info,
                complete_request=self._arbitrator.complete_request,
            )
            await self._arbitrator.handshake(self)
            await self._fetch_capabilities()
            await self._start_gnmi()
            self._channel_up()

            # Receive messages from the stream until it closes.
            await self._receive_until_closed()

        finally:
            await self._stop_gnmi()
            await self._p4client.close()
            self._channel_down()

    @TRACE
    async def _receive_until_closed(self):
        "Receive messages from stream until EOF."
        assert self._p4client is not None

        client = self._p4client

        while True:
            try:
                msg = await client.receive()
            except P4ClientError as ex:
                if not ex.status.is_election_id_used:
                    raise
                # Handle "election ID in use" error.
                await self._arbitrator.handshake(self, conflict=True)
            else:
                await self._handle_stream_message(msg)

    async def _handle_stream_message(self, msg: p4r.StreamMessageResponse):
        "Handle a P4Runtime StreamMessageResponse."

        msg_type = msg.WhichOneof("update")
        if msg_type is None:
            LOGGER.error("missing update: %r", msg)
            return

        if msg_type == "packet":
            self._stream_packet_message(msg)
        elif msg_type == "arbitration":
            await self._arbitrator.update(self, msg.arbitration)
        elif msg_type == "error":
            self._stream_error_message(msg)
        else:
            queue = self._queues.get(msg_type)
            if queue:
                if not queue.full():
                    obj = p4entity.decode_stream(msg, self.p4info)
                    queue.put_nowait(obj)

    async def __aenter__(self):
        "Similar to run() but provides a one-time context manager interface."
        assert self._p4client is None
        assert self._tasks is None

        self._tasks = SwitchTasks()
        self._p4client = P4Client(
            self._address,
            self._options.channel_credentials,
            wait_for_ready=False,
        )
        self._switch_start()

        try:
            # Start the switch's `_run` task in the background. Then, wait for
            # `_run` task to fire the CHANNEL_READY event. If the `_run` task
            # cannot connect or fails in some other way, it will finish before
            # the `ready` future. We need to handle the error in this case.

            run = self.create_task(self._run(), background=True)
            ready = self.ee.event_future(SwitchEvent.CHANNEL_READY)
            done, _ = await asyncio.wait(
                [run, ready], return_when=asyncio.FIRST_COMPLETED
            )
            if run in done:
                await run

        except BaseException:
            await self.__aexit__(None, None, None)
            raise

        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> None:
        "Similar to run() but provides a one-time context manager interface."
        assert self._p4client is not None
        assert self._tasks is not None

        self._tasks.cancel_all()
        await self._tasks.wait()
        self._arbitrator.reset()
        self._p4client = None
        self._tasks = None
        self._switch_stop()

    def _switch_start(self):
        "Called when switch starts its run() cycle."
        assert not self._is_channel_up

        LOGGER.info(
            "Switch start (name=%r, address=%r, device_id=%r, initial_election_id=%r)",
            self.name,
            self._address,
            self.device_id,
            self.options.initial_election_id,
        )
        self.ee.emit(SwitchEvent.SWITCH_START)

    def _switch_stop(self):
        "Called when switch stops its run() cycle."
        assert not self._is_channel_up

        LOGGER.info("Switch stop (name=%r)", self.name)
        self.ee.emit(SwitchEvent.SWITCH_STOP)

    def _channel_up(self):
        "Called when P4Runtime channel is UP."
        assert not self._is_channel_up

        ports = " ".join(f"({port.id}){port.name}" for port in self.ports)
        LOGGER.info(
            "Channel up (is_primary=%r, election_id=%r, primary_id=%r, p4r=%s): %s",
            self.is_primary,
            self.election_id,
            self.primary_id,
            self.api_version,
            ports,
        )
        self._is_channel_up = True
        self.create_task(self._ready())

        self.ee.emit(SwitchEvent.CHANNEL_UP, self)

    def _channel_down(self):
        "Called when P4Runtime channel is DOWN."
        if not self._is_channel_up:
            return  # do nothing!

        LOGGER.info("Channel down (is_primary=%r)", self.is_primary)
        self._is_channel_up = False

        self.ee.emit(SwitchEvent.CHANNEL_DOWN, self)

    def _become_primary(self):
        "Called when a P4Runtime backup channel becomes the primary."
        assert self._tasks is not None

        LOGGER.info(
            "Become primary (is_primary=%r, election_id=%r, primary_id=%r)",
            self.is_primary,
            self.election_id,
            self.primary_id,
        )

        self._tasks.cancel_primary()
        self.create_task(self._ready())

        self.ee.emit(SwitchEvent.BECOME_PRIMARY, self)

    def _become_backup(self):
        "Called when a P4Runtime primary channel becomes a backup."
        assert self._tasks is not None

        LOGGER.info(
            "Become backup (is_primary=%r, election_id=%r, primary_id=%r)",
            self.is_primary,
            self.election_id,
            self.primary_id,
        )

        self._tasks.cancel_primary()
        self.create_task(self._ready())

        self.ee.emit(SwitchEvent.BECOME_BACKUP, self)

    def _channel_ready(self):
        "Called when a P4Runtime channel is READY."
        LOGGER.info(
            "Channel ready (is_primary=%r): %s",
            self.is_primary,
            self.p4info.get_pipeline_info(),
        )

        if self._options.ready_handler:
            self.create_task(self._options.ready_handler(self))

        self.ee.emit(SwitchEvent.CHANNEL_READY, self)

    def _stream_packet_message(self, msg: p4r.StreamMessageResponse):
        "Called when a P4Runtime packet-in response is received."
        packet = p4entity.decode_stream(msg, self.p4info)

        was_queued = False
        for filter, queue in self._packet_queues:
            if not queue.full() and filter(packet.payload):
                queue.put_nowait(packet)
                was_queued = True

        if not was_queued:
            LOGGER.warning("packet ignored: %r", packet)

    def _stream_error_message(self, msg: p4r.StreamMessageResponse):
        "Called when a P4Runtime stream error response is received."
        assert self._p4client is not None

        # Log the message at the ERROR level.
        pbuf.log_msg(self._p4client.channel, msg, self.p4info, level=logging.ERROR)

        self.ee.emit(SwitchEvent.STREAM_ERROR, self, msg)

    @TRACE
    async def _ready(self):
        "Prepare the pipeline."

        if self.is_primary:
            # Primary: Set up pipeline or retrieve it.
            if self.p4info.is_configured:
                await self._set_pipeline()
            else:
                await self._get_pipeline()

        elif not self.p4info.is_configured:
            # Backup: Retrieve the pipeline only if it is not configured.
            # FIXME: There is a race condition with the primary client; we
            # may receive the wrong pipeline. We may need to poll the pipeline
            # cookie when we're a backup to check for changes?
            await self._get_pipeline()

        self._channel_ready()

    @TRACE
    async def _get_pipeline(self):
        "Get the switch's P4Info."

        try:
            reply = await self._get_pipeline_config_request(
                response_type=P4ConfigResponseType.P4INFO_AND_COOKIE
            )
            if reply.config.HasField("p4info"):
                self.p4info.set_p4info(reply.config.p4info)

        except P4ClientError as ex:
            if not ex.status.is_no_pipeline_configured:
                raise

    @TRACE
    async def _set_pipeline(self):
        "Set up the pipeline."

        cookie = -1
        try:
            reply = await self._get_pipeline_config_request()
            if reply.config.HasField("cookie"):
                cookie = reply.config.cookie.cookie

        except P4ClientError as ex:
            if not ex.status.is_no_pipeline_configured:
                raise

        if cookie != self.p4info.p4cookie:
            LOGGER.debug(
                "cookie %#x does not match expected %#x", cookie, self.p4info.p4cookie
            )
            await self._set_pipeline_config_request(
                config=self.p4info.get_pipeline_config()
            )
            LOGGER.info("Pipeline installed: %s", self.p4info.get_pipeline_info())

    async def _get_pipeline_config_request(
        self,
        *,
        response_type: P4ConfigResponseType = P4ConfigResponseType.COOKIE_ONLY,
    ) -> p4r.GetForwardingPipelineConfigResponse:
        "Send a GetForwardingPipelineConfigRequest and await the response."
        assert self._p4client is not None

        return await self._p4client.request(
            p4r.GetForwardingPipelineConfigRequest(
                device_id=self.device_id,
                response_type=response_type.vt(),
            )
        )

    async def _set_pipeline_config_request(
        self,
        *,
        action: P4ConfigAction = P4ConfigAction.VERIFY_AND_COMMIT,
        config: p4r.ForwardingPipelineConfig,
    ) -> p4r.SetForwardingPipelineConfigResponse:
        "Send a SetForwardingPipelineConfigRequest and await the response."
        assert self._p4client is not None

        return await self._p4client.request(
            p4r.SetForwardingPipelineConfigRequest(
                device_id=self.device_id,
                action=action.vt(),
                config=config,
            )
        )

    async def read(self, entities: Iterable[p4entity.P4EntityList]):
        "Async iterator that reads entities from the switch."
        assert self._p4client is not None

        if not entities:
            return

        request = p4r.ReadRequest(
            device_id=self.device_id,
            entities=p4entity.encode_entities(entities, self.p4info),
        )

        async for reply in self._p4client.request_iter(request):
            for ent in reply.entities:
                yield p4entity.decode_entity(ent, self.p4info)

    async def write(
        self,
        entities: Iterable[p4entity.P4UpdateList],
        *,
        strict: bool = True,
        warn_only: bool = False,
    ):
        """Write updates and stream messages to the switch.

        If `strict` is False, MODIFY and DELETE operations will NOT raise an
        error if the entity does not exist (NOT_FOUND).

        If `warn_only` is True, no operations will raise an error. Instead,
        the exception will be logged as a WARNING and the method will return
        normally.
        """
        assert self._p4client is not None

        if not entities:
            return

        msgs = p4entity.encode_updates(entities, self.p4info)

        updates: list[p4r.Update] = []
        for msg in msgs:
            if isinstance(msg, p4r.StreamMessageRequest):
                # StreamMessageRequests are transmitted immediately.
                # TODO: Understand what happens with backpressure?
                await self._p4client.send(msg)
            else:
                updates.append(msg)

        if updates:
            await self._write_request(updates, strict, warn_only)

    async def insert(
        self,
        entities: Iterable[p4entity.P4EntityList],
        *,
        warn_only: bool = False,
    ):
        """Insert the specified entities.

        If `warn_only` is True, errors will be logged as warnings instead of
        raising an exception.
        """
        if entities:
            await self._write_request(
                [
                    p4r.Update(type=p4r.Update.INSERT, entity=ent)
                    for ent in p4entity.encode_entities(entities, self.p4info)
                ],
                True,
                warn_only,
            )

    async def modify(
        self,
        entities: Iterable[p4entity.P4EntityList],
        *,
        strict: bool = True,
        warn_only: bool = False,
    ):
        """Modify the specified entities.

        If `strict` is False, NOT_FOUND errors will be ignored.

        If `warn_only` is True, errors will be logged as warnings instead of
        raising an exception.
        """
        if entities:
            await self._write_request(
                [
                    p4r.Update(type=p4r.Update.MODIFY, entity=ent)
                    for ent in p4entity.encode_entities(entities, self.p4info)
                ],
                strict,
                warn_only,
            )

    async def delete(
        self,
        entities: Iterable[p4entity.P4EntityList],
        *,
        strict: bool = True,
        warn_only: bool = False,
    ):
        """Delete the specified entities.

        If `strict` is False, NOT_FOUND errors will be ignored.

        If `warn_only` is True, errors will be logged as warnings instead of
        raising an exception.
        """
        if entities:
            await self._write_request(
                [
                    p4r.Update(type=p4r.Update.DELETE, entity=ent)
                    for ent in p4entity.encode_entities(entities, self.p4info)
                ],
                strict,
                warn_only,
            )

    async def delete_all(
        self,
        entities: Iterable[p4entity.P4EntityList] = (),
    ):
        """Delete all entities if no parameter is passed. Otherwise, delete
        items that match `entities`.

        TODO: This method does not affect indirect counters or meters.

        TODO: ActionProfileGroup/Member, ValueSet.
        """
        if entities:
            # Delete just the matching entities and return.
            return await self._wildcard_delete(entities)

        # Start by deleting everything that matches these wildcards.
        await self._wildcard_delete(
            [
                p4entity.P4TableEntry(),
                p4entity.P4MulticastGroupEntry(),
                p4entity.P4CloneSessionEntry(),
            ]
        )

        # Reset all default table entries.
        default_entries = [
            p4entity.P4TableEntry(table.alias, is_default_action=True)
            for table in self.p4info.tables
            if table.const_default_action is None and table.action_profile is None
        ]
        if default_entries:
            await self.modify(default_entries)

        # Delete DigestEntry separately. Wildcard reads are not supported.
        digest_entries = [
            p4entity.P4DigestEntry(digest.alias) for digest in self.p4info.digests
        ]
        if digest_entries:
            await self.delete(digest_entries, strict=False)

    async def _wildcard_delete(self, entities: Iterable[p4entity.P4EntityList]):
        "Delete entities that match a wildcard read."
        assert self._p4client is not None

        request = p4r.ReadRequest(
            device_id=self.device_id,
            entities=p4entity.encode_entities(entities, self.p4info),
        )

        async for reply in self._p4client.request_iter(request):
            if reply.entities:
                await self.delete(reply.entities)

    async def _write_request(
        self,
        updates: list[p4r.Update],
        strict: bool,
        warn_only: bool,
    ):
        "Send a P4Runtime WriteRequest."
        assert self._p4client is not None

        try:
            await self._p4client.request(
                p4r.WriteRequest(
                    device_id=self.device_id,
                    updates=updates,
                )
            )
        except P4ClientError as ex:
            if strict or not ex.status.is_not_found_only:
                if warn_only:
                    LOGGER.warning(
                        "WriteRequest with `warn_only=True` failed",
                        exc_info=True,
                    )
                else:
                    raise

            assert (not strict and ex.status.is_not_found_only) or warn_only

    async def _fetch_capabilities(self):
        "Check the P4Runtime protocol version supported by the other end."
        assert self._p4client is not None

        try:
            reply = await self._p4client.request(p4r.CapabilitiesRequest())
            self._api_version = ApiVersion.parse(reply.p4runtime_api_version)

        except P4ClientError as ex:
            if not ex.is_unimplemented:
                raise
            LOGGER.warning("CapabilitiesRequest is not implemented")

    async def _start_gnmi(self):
        "Start the associated gNMI client."
        assert self._gnmi_client is None
        assert self._p4client is not None

        self._gnmi_client = gNMIClient(self._address, self._options.channel_credentials)
        await self._gnmi_client.open(channel=self._p4client.channel)

        try:
            await self._ports.subscribe(self._gnmi_client)
            self.create_task(self._ports.update(), background=True, name="_ports")

        except gNMIClientError as ex:
            if not ex.is_unimplemented:
                raise
            LOGGER.warning("gNMI is not implemented")
            await self._gnmi_client.close()
            self._gnmi_client = None

    async def _stop_gnmi(self):
        "Stop the associated gNMI client."
        if self._gnmi_client is not None:
            self._ports.close()
            await self._gnmi_client.close()
            self._gnmi_client = None

    def __repr__(self):
        "Return string representation of switch."
        return f"Switch(name={self._name!r}, address={self._address!r})"


class SwitchEvent(str, enum.Enum):
    "Events for Switch class."

    CONTROLLER_ENTER = "controller_enter"  # (switch)
    CONTROLLER_LEAVE = "controller_leave"  # (switch)
    SWITCH_START = "switch_start"  # (switch)
    SWITCH_STOP = "switch_stop"  # (switch)
    CHANNEL_UP = "channel_up"  # (switch)
    CHANNEL_DOWN = "channel_down"  # (switch)
    CHANNEL_READY = "channel_ready"  # (switch)
    BECOME_PRIMARY = "become_primary"  # (switch)
    BECOME_BACKUP = "become_backup"  # (switch)
    PORT_UP = "port_up"  # (switch, port)
    PORT_DOWN = "port_down"  # (switch, port)
    STREAM_ERROR = "stream_error"  # (switch, p4r.StreamMessageResponse)


class SwitchEmitter(pyee.EventEmitter):
    "EventEmitter subclass for emitting Switch events."

    def __init__(self, switch: Switch):
        super().__init__()
        self._switch = switch

    def _emit_run(self, f: Any, args: Any, kwargs: Any):
        try:
            coro: Any = f(*args, **kwargs)
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.error("Error in SwitchEmitter._emit_run", exc_info=exc)
            # TODO: Have synchronous callback failures affect Switch?
        else:
            if asyncio.iscoroutine(coro):
                self._switch.create_task(coro)

    def event_future(self, event: SwitchEvent):
        "Future to wait for a specific event."

        ready = asyncio.get_running_loop().create_future()
        self.once(event, lambda _: ready.set_result(None))  # type: ignore
        return ready


class SwitchTasks:
    "Manage a set of related tasks."

    _tasks: set[asyncio.Task[Any]]
    _task_count: CountdownFuture

    def __init__(self):
        self._tasks = set()
        self._task_count = CountdownFuture()

    def create_task(
        self,
        coro: Coroutine[Any, Any, _T],
        *,
        switch: Switch,
        background: bool,
        name: str | None = None,
    ) -> asyncio.Task[_T]:
        "Create a new task managed by switch."
        if name is None:
            name = coro.__qualname__

        bg_char = "&" if background else ""
        task_name = f"fy:{switch.name}|{name}{bg_char}"

        task = asyncio.create_task(coro, name=task_name)
        self._tasks.add(task)
        self._task_count.increment()
        task.add_done_callback(self._task_done)

        return task

    def _task_done(self, done: asyncio.Task[Any]):
        "Called when a task finishes."
        self._tasks.remove(done)
        self._task_count.decrement()

        if not done.cancelled():
            ex = done.exception()
            if ex is not None:
                self.cancel_all()

                # If the exception is GRPCStatusCode.UNAVAILABLE, don't report
                # an error.
                if getattr(ex, "code", None) == GRPCStatusCode.UNAVAILABLE:
                    LOGGER.debug("Switch task %r failed: UNAVAILABLE", done.get_name())
                else:
                    LOGGER.error("Switch task %r failed", done.get_name(), exc_info=ex)

    def cancel_all(self):
        "Cancel all tasks."
        for task in self._tasks:
            if not task.done():
                task.cancel()

    def cancel_primary(self):
        "Cancel all non-background tasks."
        for task in self._tasks:
            if not task.done() and not task.get_name().endswith("&"):
                task.cancel()

    @TRACE
    async def wait(self):
        "Wait for all tasks to finish."
        await self._task_count.wait(self.cancel_all)


@asynccontextmanager
async def _throttle_failure():
    "Used to throttle retries, if the switch's lifecycle fails too quickly."

    start_time = time.monotonic()
    yield
    end_time = time.monotonic()

    if end_time - start_time < _FAIL_MIN_TIME_SECS:
        # Handle case where we failed too quickly.
        LOGGER.warning(
            "Switch failed in less than %g seconds; waiting %g seconds to try again",
            _FAIL_MIN_TIME_SECS,
            _FAIL_THROTTLE_SECS,
        )
        await asyncio.sleep(_FAIL_THROTTLE_SECS)

    else:
        # Otherwise, always yield to other tasks here.
        await asyncio.sleep(0)
