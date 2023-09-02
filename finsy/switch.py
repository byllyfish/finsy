"Implements the Switch class."

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

import asyncio
import dataclasses
import enum
import logging
import re
import time
from asyncio import Queue
from contextlib import asynccontextmanager
from pathlib import Path
from types import TracebackType
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterator,
    Callable,
    Coroutine,
    Iterable,
    NamedTuple,
    SupportsBytes,
    TypeVar,
    overload,
)

import pyee
from typing_extensions import Self

from finsy import p4entity, pbuf
from finsy.futures import CountdownFuture
from finsy.gnmiclient import GNMIClient, GNMIClientError
from finsy.grpcutil import GRPCCredentialsTLS, GRPCStatusCode
from finsy.log import LOGGER
from finsy.p4arbitrator import Arbitrator
from finsy.p4client import P4Client, P4ClientError
from finsy.p4schema import P4ConfigAction, P4ConfigResponseType, P4Schema
from finsy.ports import SwitchPortList
from finsy.proto import p4r

# Maximum size of queues used for PacketIn, DigestList, etc.

_DEFAULT_QUEUE_SIZE = 50

# If switch fails to run for longer than _FAIL_MIN_TIME_SECS, wait
# _FAIL_THROTTLE_SECS before trying again.

_FAIL_MIN_TIME_SECS = 2.0
_FAIL_THROTTLE_SECS = 10.0

_T = TypeVar("_T")
_ET = TypeVar("_ET", bound=p4entity.P4Entity)


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

    p4force: bool = False
    "If true, always load the P4 program after initial handshake."

    device_id: int = 1
    "Default P4Runtime device ID."

    initial_election_id: int = 10
    "Initial P4Runtime election ID."

    channel_credentials: GRPCCredentialsTLS | None = None
    "P4Runtime channel credentials. Used for TLS support."

    role_name: str = ""
    "P4Runtime role configuration."

    role_config: pbuf.PBMessage | None = None
    "P4Runtime role configuration."

    ready_handler: Callable[["Switch"], Coroutine[Any, Any, None]] | None = None
    "Ready handler async function callback."

    fail_fast: bool = False
    """If true, log switch errors as CRITICAL and immediately abort when the
    switch is running in a Controller."""

    configuration: Any = None
    "Store your app's configuration information here."

    def __call__(self, **kwds: Any) -> Self:
        return dataclasses.replace(self, **kwds)


_SEMVER_REGEX = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?(.*)$")


class ApiVersion(NamedTuple):
    "Represents the semantic version of an API."

    major: int
    minor: int
    patch: int
    extra: str  # optional pre-release/build info

    @classmethod
    def parse(cls, version_str: str) -> Self:
        "Parse the API version string."
        m = _SEMVER_REGEX.match(version_str.strip())
        if not m:
            raise ValueError(f"unexpected version string: {version_str}")
        return cls(int(m[1]), int(m[2]), int(m[3] or "0"), m[4])

    def __str__(self) -> str:
        "Return the version string."
        vers = self[:3]  # pylint: disable=unsubscriptable-object
        return ".".join(map(str, vers)) + self.extra


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
    _packet_queues: list[tuple[Callable[[bytes], bool], Queue[p4entity.P4PacketIn]]]
    _digest_queues: dict[str, Queue[p4entity.P4DigestList]]
    _timeout_queue: Queue[p4entity.P4IdleTimeoutNotification] | None
    _arbitrator: "Arbitrator"
    _gnmi_client: GNMIClient | None
    _ports: SwitchPortList
    _is_channel_up: bool = False
    _api_version: ApiVersion = ApiVersion(1, 0, 0, "")

    control_task: asyncio.Task[Any] | None = None
    "Used by Controller to track switch's main task."

    ee: "SwitchEmitter"
    "Event emitter."

    manager: Any = None
    "Available to attach per-switch manager(s)."

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
        self._packet_queues = []
        self._digest_queues = {}
        self._timeout_queue = None
        self._arbitrator = Arbitrator(
            options.initial_election_id, options.role_name, options.role_config
        )
        self._gnmi_client = None
        self._ports = SwitchPortList()
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
    def options(self, opts: SwitchOptions) -> None:
        "Set switch options to a new value."
        if self._p4client is not None:
            raise RuntimeError("Cannot change switch options while client is open.")

        self._options = opts
        self._p4schema = P4Schema(opts.p4info, opts.p4blob)
        self._arbitrator = Arbitrator(
            opts.initial_election_id, opts.role_name, opts.role_config
        )

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
    def role_name(self) -> str:
        "Switch's current role name."
        return self._arbitrator.role_name

    @property
    def p4info(self) -> P4Schema:
        "Switch's P4 schema."
        return self._p4schema

    @property
    def gnmi_client(self) -> GNMIClient | None:
        "Switch's gNMI client."
        return self._gnmi_client

    @property
    def ports(self) -> SwitchPortList:
        "Switch's list of interfaces."
        return self._ports

    @property
    def api_version(self) -> ApiVersion:
        "P4Runtime protocol version."
        return self._api_version

    @overload
    async def read(
        self,
        entities: _ET,
    ) -> AsyncGenerator[_ET, None]:
        "Overload for read of a single P4Entity subtype."
        ...  # pragma: no cover

    @overload
    async def read(
        self,
        entities: Iterable[_ET],
    ) -> AsyncGenerator[_ET, None]:
        "Overload for read of an iterable of the same P4Entity subtype."
        ...  # pragma: no cover

    @overload
    async def read(
        self,
        entities: Iterable[p4entity.P4EntityList],
    ) -> AsyncGenerator[p4entity.P4Entity, None]:
        "Most general overload: we can't determine the return type exactly."
        ...  # pragma: no cover

    async def read(
        self,
        entities: Iterable[p4entity.P4EntityList] | p4entity.P4Entity,
    ) -> AsyncGenerator[p4entity.P4Entity, None]:
        "Async iterator that reads entities from the switch."
        assert self._p4client is not None

        if not entities:
            return

        if isinstance(entities, p4entity.P4Entity):
            entities = [entities]

        request = p4r.ReadRequest(
            device_id=self.device_id,
            entities=p4entity.encode_entities(entities, self.p4info),
        )

        async for reply in self._p4client.request_iter(request):
            for ent in reply.entities:
                yield p4entity.decode_entity(ent, self.p4info)

    async def read_packets(
        self,
        *,
        queue_size: int = _DEFAULT_QUEUE_SIZE,
        eth_types: Iterable[int] | None = None,
    ) -> AsyncIterator["p4entity.P4PacketIn"]:
        "Async iterator for incoming packets (P4PacketIn)."
        LOGGER.debug("read_packets: opening queue: eth_types=%r", eth_types)

        if eth_types is None:

            def _pkt_filter(_payload: bytes) -> bool:
                return True

        else:
            _filter = {eth.to_bytes(2, "big") for eth in eth_types}

            def _pkt_filter(_payload: bytes) -> bool:
                return _payload[12:14] in _filter

        queue = Queue[p4entity.P4PacketIn](queue_size)
        queue_filter = (_pkt_filter, queue)
        self._packet_queues.append(queue_filter)

        try:
            while True:
                yield await queue.get()
        finally:
            LOGGER.debug("read_packets: closing queue: eth_types=%r", eth_types)
            self._packet_queues.remove(queue_filter)

    async def read_digests(
        self,
        digest_id: str,
        *,
        queue_size: int = _DEFAULT_QUEUE_SIZE,
    ) -> AsyncIterator["p4entity.P4DigestList"]:
        "Async iterator for incoming digest lists (P4DigestList)."
        LOGGER.debug("read_digests: opening queue: digest_id=%r", digest_id)

        if digest_id in self._digest_queues:
            raise ValueError(f"queue for digest_id {digest_id!r} already open")

        queue = Queue[p4entity.P4DigestList](queue_size)
        self._digest_queues[digest_id] = queue
        try:
            while True:
                yield await queue.get()
        finally:
            LOGGER.debug("read_digests: closing queue: digest_id=%r", digest_id)
            del self._digest_queues[digest_id]

    async def read_idle_timeouts(
        self,
        *,
        queue_size: int = _DEFAULT_QUEUE_SIZE,
    ) -> AsyncIterator["p4entity.P4IdleTimeoutNotification"]:
        "Async iterator for incoming idle timeouts (P4IdleTimeoutNotification)."
        LOGGER.debug("read_idle_timeouts: opening queue")

        if self._timeout_queue is not None:
            raise ValueError("timeout queue already open")

        queue = Queue[p4entity.P4IdleTimeoutNotification](queue_size)
        self._timeout_queue = queue
        try:
            while True:
                yield await queue.get()
        finally:
            LOGGER.debug("read_idle_timeouts: closing queue")
            self._timeout_queue = None

    async def write(
        self,
        entities: Iterable[p4entity.P4UpdateList],
        *,
        strict: bool = True,
        warn_only: bool = False,
    ) -> None:
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
    ) -> None:
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
    ) -> None:
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
    ) -> None:
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

    async def delete_all(self) -> None:
        """Delete all entities if no parameter is passed. Otherwise, delete
        items that match `entities`.

        This method does not attempt to delete entries in const tables.

        TODO: This method does not affect indirect counters, meters or
        value_sets.
        """
        await self.delete_many(
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

        # Delete all P4ActionProfileGroup's and P4ActionProfileMember's.
        # We do this after deleting the P4TableEntry's in case a client is using
        # "one-shot" references; these are incompatible with separate
        # action profiles.
        await self.delete_many(
            [
                p4entity.P4ActionProfileGroup(),
                p4entity.P4ActionProfileMember(),
            ]
        )

        # Delete DigestEntry separately. Wildcard reads are not supported.
        digest_entries = [
            p4entity.P4DigestEntry(digest.alias) for digest in self.p4info.digests
        ]
        if digest_entries:
            await self.delete(digest_entries, strict=False)

    async def delete_many(self, entities: Iterable[p4entity.P4EntityList]) -> None:
        """Delete entities that match a wildcard read.

        This method always skips over entries in const tables. It is an error
        to attempt to delete those.
        """
        assert self._p4client is not None

        request = p4r.ReadRequest(
            device_id=self.device_id,
            entities=p4entity.encode_entities(entities, self.p4info),
        )

        # Compute set of all const table ID's (may be empty).
        to_skip = {table.id for table in self.p4info.tables if table.is_const}

        async for reply in self._p4client.request_iter(request):
            if reply.entities:
                if to_skip:
                    await self.delete(
                        reply
                        for reply in reply.entities
                        if reply.HasField("table_entry")
                        and reply.table_entry.table_id not in to_skip
                    )
                else:
                    await self.delete(reply.entities)

    async def run(self) -> None:
        "Run the switch's lifecycle repeatedly."
        assert self._p4client is None
        assert self._tasks is None

        self._tasks = SwitchTasks(self._options.fail_fast)
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

    async def _receive_until_closed(self):
        "Receive messages from stream until EOF."
        assert self._p4client is not None

        client = self._p4client

        while True:
            try:
                msg = await client.receive()
            except P4ClientError as ex:
                if not ex.is_election_id_used:
                    raise
                # Handle "election ID in use" error.
                await self._arbitrator.handshake(self, conflict=True)
            else:
                await self._handle_stream_message(msg)

    async def _handle_stream_message(self, msg: p4r.StreamMessageResponse):
        "Handle a P4Runtime StreamMessageResponse."
        match msg.WhichOneof("update"):
            case "packet":
                self._stream_packet_message(msg)
            case "digest":
                self._stream_digest_message(msg)
            case "idle_timeout_notification":
                self._stream_timeout_message(msg)
            case "arbitration":
                await self._arbitrator.update(self, msg.arbitration)
            case "error":
                self._stream_error_message(msg)
            case other:
                LOGGER.error("_handle_stream_message: unknown update %r", other)

    async def __aenter__(self) -> Self:
        "Similar to run() but provides a one-time context manager interface."
        assert self._p4client is None
        assert self._tasks is None

        self._tasks = SwitchTasks(self._options.fail_fast)
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
    ) -> bool | None:
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
            "Switch start (name=%r, address=%r, device_id=%r, role_name=%r, initial_election_id=%r)",
            self.name,
            self.address,
            self.device_id,
            self.role_name,
            self.options.initial_election_id,
        )
        self.ee.emit(SwitchEvent.SWITCH_START)

    def _switch_stop(self):
        "Called when switch stops its run() cycle."
        assert not self._is_channel_up

        LOGGER.info(
            "Switch stop (name=%r, address=%r, device_id=%r, role_name=%r)",
            self.name,
            self.address,
            self.device_id,
            self.role_name,
        )
        self.ee.emit(SwitchEvent.SWITCH_STOP)

    def _channel_up(self):
        "Called when P4Runtime channel is UP."
        assert not self._is_channel_up

        ports = " ".join(f"({port.id}){port.name}" for port in self.ports)
        LOGGER.info(
            "Channel up (is_primary=%r, role_name=%r, p4r=%s): %s",
            self.is_primary,
            self.role_name,
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

        LOGGER.info(
            "Channel down (is_primary=%r, role_name=%r)",
            self.is_primary,
            self.role_name,
        )
        self._is_channel_up = False

        self.ee.emit(SwitchEvent.CHANNEL_DOWN, self)

    def _become_primary(self):
        "Called when a P4Runtime backup channel becomes the primary."
        assert self._tasks is not None

        LOGGER.info(
            "Become primary (is_primary=%r, role_name=%r)",
            self.is_primary,
            self.role_name,
        )

        self._tasks.cancel_primary()
        self.create_task(self._ready())

        self.ee.emit(SwitchEvent.BECOME_PRIMARY, self)

    def _become_backup(self):
        "Called when a P4Runtime primary channel becomes a backup."
        assert self._tasks is not None

        LOGGER.info(
            "Become backup (is_primary=%r, role_name=%r)",
            self.is_primary,
            self.role_name,
        )

        self._tasks.cancel_primary()
        self.create_task(self._ready())

        self.ee.emit(SwitchEvent.BECOME_BACKUP, self)

    def _channel_ready(self):
        "Called when a P4Runtime channel is READY."
        LOGGER.info(
            "Channel ready (is_primary=%r, role_name=%r): %s",
            self.is_primary,
            self.role_name,
            self.p4info.get_pipeline_info(),
        )

        if self._options.ready_handler:
            self.create_task(self._options.ready_handler(self))

        self.ee.emit(SwitchEvent.CHANNEL_READY, self)

    def _stream_packet_message(self, msg: p4r.StreamMessageResponse):
        "Called when a P4Runtime packet-in response is received."
        packet = p4entity.decode_stream(msg, self.p4info)

        was_queued = False
        for pkt_filter, queue in self._packet_queues:
            if not queue.full() and pkt_filter(packet.payload):
                queue.put_nowait(packet)
                was_queued = True

        if not was_queued:
            LOGGER.warning("packet ignored: %r", packet)

    def _stream_digest_message(self, msg: p4r.StreamMessageResponse):
        "Called when a P4Runtime digest response is received."
        try:
            # Decode the digest list message.
            digest: p4entity.P4DigestList = p4entity.decode_stream(msg, self.p4info)
        except ValueError as ex:
            # It's possible to receive a digest for a different P4Info file, or
            # even before a P4Info is fetched from the switch.
            LOGGER.warning("digest decode failed: %s", ex)
        else:
            # Place the decoded digest list in a queue, if one is waiting.
            queue = self._digest_queues.get(digest.digest_id)
            if queue is not None and not queue.full():
                queue.put_nowait(digest)
            else:
                LOGGER.warning("digest ignored: %r", digest)

    def _stream_timeout_message(self, msg: p4r.StreamMessageResponse):
        "Called when a P4Runtime timeout notification is received."
        timeout: p4entity.P4IdleTimeoutNotification = p4entity.decode_stream(
            msg, self.p4info
        )
        queue = self._timeout_queue

        if queue is not None and not queue.full():
            queue.put_nowait(timeout)
        else:
            LOGGER.warning("timeout ignored: %r", timeout)

    def _stream_error_message(self, msg: p4r.StreamMessageResponse):
        "Called when a P4Runtime stream error response is received."
        assert self._p4client is not None

        # Log the message at the ERROR level.
        pbuf.log_msg(self._p4client.channel, msg, self.p4info, level=logging.ERROR)

        self.ee.emit(SwitchEvent.STREAM_ERROR, self, msg)

    async def _ready(self):
        "Prepare the pipeline."
        if self.p4info.is_authoritative and self.is_primary:
            await self._set_pipeline()
        else:
            await self._get_pipeline()

        self._channel_ready()

    async def _get_pipeline(self):
        "Get the switch's P4Info."
        has_pipeline = False

        try:
            reply = await self._get_pipeline_config_request(
                response_type=P4ConfigResponseType.P4INFO_AND_COOKIE
            )

            if reply.config.HasField("p4info"):
                has_pipeline = True
                p4info = reply.config.p4info
                if not self.p4info.exists:
                    # If we don't have P4Info yet, set it.
                    self.p4info.set_p4info(p4info)
                elif not self.p4info.has_p4info(p4info):
                    # If P4Info is not identical, log a warning message.
                    LOGGER.warning("Retrieved P4Info is different than expected!")

        except P4ClientError as ex:
            if not ex.is_pipeline_missing:
                raise

        if not has_pipeline and self.p4info.exists:
            LOGGER.warning("Forwarding pipeline is not configured")

    async def _set_pipeline(self):
        """Set up the pipeline.

        If `p4force` is false (the default), we first retrieve the cookie for
        the current pipeline and see if it matches the new pipeline's cookie.
        If the cookies match, we are done; there is no need to set the pipeline.

        If `p4force` is true, we always load the new pipeline.
        """
        cookie = -1
        try:
            if not self.options.p4force:
                reply = await self._get_pipeline_config_request()
                if reply.config.HasField("cookie"):
                    cookie = reply.config.cookie.cookie

        except P4ClientError as ex:
            if not ex.is_pipeline_missing:
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
            if strict or not ex.is_not_found_only:
                if warn_only:
                    LOGGER.warning(
                        "WriteRequest with `warn_only=True` failed",
                        exc_info=True,
                    )
                else:
                    raise

            assert (not strict and ex.is_not_found_only) or warn_only

    async def _fetch_capabilities(self):
        "Check the P4Runtime protocol version supported by the other end."
        assert self._p4client is not None

        try:
            reply = await self._p4client.request(p4r.CapabilitiesRequest())
            self._api_version = ApiVersion.parse(reply.p4runtime_api_version)

        except P4ClientError as ex:
            if ex.code != GRPCStatusCode.UNIMPLEMENTED:
                raise
            LOGGER.warning("CapabilitiesRequest is not implemented")

    async def _start_gnmi(self):
        "Start the associated gNMI client."
        assert self._gnmi_client is None
        assert self._p4client is not None

        self._gnmi_client = GNMIClient(self._address, self._options.channel_credentials)
        await self._gnmi_client.open(channel=self._p4client.channel)

        try:
            await self._ports.subscribe(self._gnmi_client)
            if self._ports:
                self.create_task(self._ports.listen(), background=True, name="_ports")

        except GNMIClientError as ex:
            if ex.code != GRPCStatusCode.UNIMPLEMENTED:
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

    def __repr__(self) -> str:
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

    def event_future(self, event: SwitchEvent) -> asyncio.Future[Any]:
        "Future to wait for a specific event."
        ready = asyncio.get_running_loop().create_future()
        self.once(event, lambda _: ready.set_result(None))  # type: ignore
        return ready


class SwitchFailFastError(BaseException):
    "This exception is raised when a Switch with `fail_fast=True` fails."


class SwitchTasks:
    "Manage a set of related tasks."

    _tasks: set[asyncio.Task[Any]]
    _task_count: CountdownFuture
    _fail_fast: bool
    _fail_count: int

    def __init__(self, fail_fast: bool):
        self._tasks = set()
        self._task_count = CountdownFuture()
        self._fail_fast = fail_fast
        self._fail_count = 0

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
                    self._fail_count += 1
                    LOGGER.critical(
                        "Switch task %r failed", done.get_name(), exc_info=ex
                    )

    def cancel_all(self) -> None:
        "Cancel all tasks."
        for task in self._tasks:
            if not task.done():
                task.cancel()

    def cancel_primary(self) -> None:
        "Cancel all non-background tasks."
        for task in self._tasks:
            if not task.done() and not task.get_name().endswith("&"):
                task.cancel()

    async def wait(self) -> None:
        "Wait for all tasks to finish."
        try:
            await self._task_count.wait(self.cancel_all)
        finally:
            if self._fail_fast and self._fail_count > 0:
                raise SwitchFailFastError()


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
