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
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from types import TracebackType
from typing import Any, AsyncIterator, Callable, Coroutine, SupportsBytes, TypeVar

import grpc  # pyright: ignore[reportMissingTypeStubs]
import pyee

from finsy import p4entity
from finsy.arbitrator import Arbitrator
from finsy.gnmiclient import gNMIClient, gNMIClientError
from finsy.log import LOGGER, TRACE
from finsy.p4client import P4Client, P4ClientError
from finsy.p4schema import P4ConfigAction, P4ConfigResponseType, P4Schema, P4UpdateType
from finsy.ports import PortList
from finsy.proto import p4r
from finsy.util import CountdownFuture

# Maximum size of queues used for PacketIn, DigestList, etc.

_DEFAULT_QUEUE_SIZE = 50

# If switch fails to run for longer than _FAIL_MIN_TIME_SECS, wait
# _FAIL_THROTTLE_SECS before trying again.

_FAIL_MIN_TIME_SECS = 2.0
_FAIL_THROTTLE_SECS = 10.0

_ApiVersion = tuple[int, int, int]

_T = TypeVar("_T")


@dataclasses.dataclass(frozen=True)
class SwitchOptions:
    """`SwitchOptions` manages the configuration options for a `Switch`.

    Each `SwitchOptions` object is immutable and may be shared by multiple
    switches. Although each object is immutable, you can use function call
    syntax to change one or more properties and construct a new object.

    ```
    opts = SwitchOptions(device_id=5)
    new_opts = opts(device_id=6)
    ```
    """

    p4info: Path | None = None
    p4blob: Path | SupportsBytes | None = None
    device_id: int = 1
    initial_election_id: int = 10
    credentials: grpc.ChannelCredentials | None = None
    ready_handler: Callable[["Switch"], Coroutine[Any, Any, None]] | None = None

    def __call__(self, **kwds: Any):
        return dataclasses.replace(self, **kwds)


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
    _arbitrator: "Arbitrator"
    _gnmi_client: gNMIClient | None
    _ports: PortList
    _is_channel_up: bool = False
    _api_version: _ApiVersion = (1, 0, 0)

    control_task: asyncio.Task[Any] | None = None
    "Used by Controller to track switch's main task."

    ee: "SwitchEmitter"
    "Event emitter."

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
        self._arbitrator = Arbitrator(options.initial_election_id)
        self._gnmi_client = None
        self._ports = PortList()
        self.ee = SwitchEmitter(self)

    @property
    def name(self) -> str:
        return self._name

    @property
    def options(self) -> SwitchOptions:
        return self._options

    @options.setter
    def options(self, opts: SwitchOptions):
        if self._p4client is not None:
            raise RuntimeError("Cannot change switch options while client is open.")

        self._options = opts
        self._p4schema = P4Schema(opts.p4info, opts.p4blob)
        self._arbitrator = Arbitrator(opts.initial_election_id)

    @property
    def device_id(self) -> int:
        return self._options.device_id

    @property
    def is_primary(self) -> bool:
        return self._arbitrator.is_primary

    @property
    def primary_id(self) -> int:
        return self._arbitrator.primary_id

    @property
    def election_id(self) -> int:
        return self._arbitrator.election_id

    @property
    def p4info(self) -> P4Schema:
        return self._p4schema

    @property
    def p4client(self) -> P4Client:
        assert self._p4client is not None
        return self._p4client

    @property
    def ports(self) -> PortList:
        return self._ports

    @property
    def api_version(self) -> _ApiVersion:
        return self._api_version

    @property
    def api_version_string(self) -> str:
        return ".".join(map(str, self.api_version))

    def packet_iterator(
        self,
        *,
        size: int = _DEFAULT_QUEUE_SIZE,
    ) -> AsyncIterator["p4entity.P4PacketIn"]:
        return self._queue_iter("packet", size)

    def digest_iterator(
        self,
        *,
        size: int = _DEFAULT_QUEUE_SIZE,
    ) -> AsyncIterator["p4entity.P4DigestList"]:
        return self._queue_iter("digest", size)

    async def _queue_iter(self, name: str, size: int) -> AsyncIterator[Any]:
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
        self._p4client = P4Client(self._address, self._options.credentials)

        try:
            while True:
                # If the switch fails and restarts too quickly, slow it down.
                async with _throttle_failure():
                    await self._run_lifecycle()

        finally:
            self._p4client = None
            self._tasks = None

    @TRACE
    async def _run_lifecycle(self):
        "Run the switch's lifecycle once."
        assert self._tasks is not None

        self.create_task(self._run(), background=True)
        await self._tasks.wait()
        self._arbitrator.reset()

    def create_task(
        self,
        coro: Coroutine[Any, Any, _T],
        *,
        background: bool = False,
        name: str | None = None,
    ) -> asyncio.Task[_T]:
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

        if msg_type == "arbitration":
            await self._arbitrator.update(self, msg.arbitration)
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
        self._p4client = P4Client(self._address, self._options.credentials)
        self.create_task(self._run(), background=True)

        try:
            # Wait for CHANNEL_READY event from the switch.
            await self.ee.wait_for_event(SwitchEvent.CHANNEL_READY)
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

    def _channel_up(self):
        assert not self._is_channel_up

        ports = " ".join(f"({port.id}){port.name}" for port in self.ports)
        LOGGER.info(
            "Channel up (is_primary=%r, election_id=%r, primary_id=%r, api_version=%s): %s",
            self.is_primary,
            self.election_id,
            self.primary_id,
            self.api_version_string,
            ports,
        )
        self._is_channel_up = True
        self.create_task(self._ready())

        self.ee.emit(SwitchEvent.CHANNEL_UP, self)

    def _channel_down(self):
        if not self._is_channel_up:
            return  # do nothing!

        LOGGER.info(
            "Channel down (is_primary=%r, election_id=%r, primary_id=%r)",
            self.is_primary,
            self.election_id,
            self.primary_id,
        )
        self._is_channel_up = False

        self.ee.emit(SwitchEvent.CHANNEL_DOWN, self)

    def _become_primary(self):
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
        LOGGER.info("Channel ready (is_primary=%r)", self.is_primary)

        if self._options.ready_handler:
            self.create_task(self._options.ready_handler(self))

        self.ee.emit(SwitchEvent.CHANNEL_READY, self)

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

    async def read(self, *entities: p4entity.EntityList):
        assert self._p4client is not None

        request = p4r.ReadRequest(
            device_id=self.device_id,
            entities=p4entity.encode_entities(entities, self.p4info),
        )

        async for reply in self._p4client.request_iter(request):
            for ent in reply.entities:
                yield p4entity.decode_entity(ent, self.p4info)

    async def write(self, *entities: p4entity.UpdateList):
        assert self._p4client is not None

        msgs = p4entity.encode_updates(entities, self.p4info)

        updates: list[p4r.Update] = []
        for msg in msgs:
            if isinstance(msg, p4r.StreamMessageRequest):
                await self._p4client.send(msg)
            else:
                updates.append(msg)

        if updates:
            await self._p4client.request(
                p4r.WriteRequest(
                    device_id=self.device_id,
                    updates=updates,
                )
            )

    async def insert(self, *entities: p4entity.EntityList):
        await self._write(entities, P4UpdateType.INSERT)

    async def modify(self, *entities: p4entity.EntityList):
        await self._write(entities, P4UpdateType.MODIFY)

    async def delete(
        self,
        *entities: p4entity.EntityList,
        ignore_not_found_error: bool = False,
    ):
        """Delete the specified entities.

        It is an error to delete entities that do not exist. If
        `ignore_not_found_error` is True, this 'NOT FOUND' error will be
        suppressed.
        """
        try:
            await self._write(entities, P4UpdateType.DELETE)
        except P4ClientError as ex:
            if ignore_not_found_error and ex.status.is_not_found_only:
                return
            raise

    async def delete_all(self):
        assert self._p4client is not None

        everything = [
            p4entity.P4TableEntry(),
            p4entity.P4MulticastGroupEntry(),
            # TODO: This isn't everything...
        ]

        request = p4r.ReadRequest(
            device_id=self.device_id,
            entities=p4entity.encode_entities(everything, self.p4info),
        )

        async for reply in self._p4client.request_iter(request):
            if reply.entities:
                await self.delete(reply.entities)

        # We need to delete DigestEntry separately. Wildcard reads are not
        # supported.
        digest_entries = [
            p4entity.P4DigestEntry(digest.alias) for digest in self.p4info.digests
        ]
        if digest_entries:
            await self.delete(digest_entries, ignore_not_found_error=True)

    async def _write(self, entities: p4entity.EntityList, update_type: P4UpdateType):
        assert self._p4client is not None

        updates = [
            p4r.Update(type=update_type.vt(), entity=ent)
            for ent in p4entity.encode_entities(entities, self.p4info)
        ]
        await self._p4client.request(
            p4r.WriteRequest(
                device_id=self.device_id,
                updates=updates,
            )
        )

    async def _fetch_capabilities(self):
        "Check the P4Runtime protocol version supported by the other end."
        assert self._p4client is not None

        try:
            reply = await self._p4client.request(p4r.CapabilitiesRequest())
            self._api_version = _parse_semantic_version(reply.p4runtime_api_version)

        except P4ClientError as ex:
            if not ex.is_unimplemented:
                raise
            LOGGER.warning("CapabilitiesRequest is not implemented")

    async def _start_gnmi(self):
        assert self._gnmi_client is None
        assert self._p4client is not None

        self._gnmi_client = gNMIClient(self._address, self._options.credentials)
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
        if self._gnmi_client is not None:
            self._ports.close()
            await self._gnmi_client.close()
            self._gnmi_client = None

    def __repr__(self):
        return f"Switch(name={self._name!r}, address={self._address!r})"


class SwitchEvent(str, enum.Enum):
    "Events for Switch class."

    CHANNEL_UP = "channel_up"  # (switch)
    CHANNEL_DOWN = "channel_down"  # (switch)
    CHANNEL_READY = "channel_ready"  # (switch)
    BECOME_PRIMARY = "become_primary"  # (switch)
    BECOME_BACKUP = "become_backup"  # (switch)
    PORT_UP = "port_up"  # (switch, port)
    PORT_DOWN = "port_down"  # (switch, port)
    SWITCH_DONE = "switch_done"  # (switch)


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

    async def wait_for_event(self, event: SwitchEvent):
        "Wait for a specific event."

        ready = asyncio.Event()
        self.once(event, lambda _: ready.set())  # type: ignore
        await ready.wait()


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
            name = coro.__name__

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
                LOGGER.error("Switch task %r failed", done.get_name(), exc_info=ex)
                self.cancel_all()

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


_SEMVER_REGEX = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def _parse_semantic_version(version_str: str) -> _ApiVersion:
    "Parse version string and return a 3-tuple (major, minor, patch)."

    m = _SEMVER_REGEX.match(version_str)
    if not m:
        raise ValueError(f"unexpected version string: {version_str}")

    return (int(m[1]), int(m[2]), int(m[3]))
