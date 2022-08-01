"Implements entity encode/decode functions."

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

import collections.abc
from dataclasses import KW_ONLY, dataclass
from typing import Any, Iterator, NoReturn, Protocol, Sequence

from typing_extensions import Self

from finsy.log import LOGGER
from finsy.p4schema import P4Action, P4ActionRef, P4Schema, P4Table, P4UpdateType
from finsy.proto import p4r


class _SupportsDecode(Protocol):
    # FIXME: This is a class method that returns an instance of that class.
    def decode(self, msg: Any, schema: P4Schema) -> Any:
        ...


class _SupportsEncodeEntity(Protocol):
    def encode(self, schema: P4Schema) -> p4r.Entity:
        ...


class _SupportsEncodeUpdate(Protocol):
    def encode_update(self, schema: P4Schema) -> p4r.Update | p4r.StreamMessageRequest:
        ...


_DECODER: dict[str, _SupportsDecode] = {}


def decodable(key: str):
    "Class decorator to specify the class used to decode P4Runtime messages."

    def _decorate(cls: Any):
        assert key not in _DECODER
        _DECODER[key] = cls
        return cls

    return _decorate


def decode_entity(msg: p4r.Entity, schema: P4Schema) -> Any:
    "Decode a P4Runtime Entity to the Python class registered in _DECODER."

    key = msg.WhichOneof("entity")
    if key is None:
        raise ValueError("missing entity")

    if key == "packet_replication_engine_entry":
        submsg = msg.packet_replication_engine_entry
        key = submsg.WhichOneof("type")
        if key is None:
            raise ValueError("missing type")

    return _DECODER[key].decode(msg, schema)


def decode_stream(msg: p4r.StreamMessageResponse, schema: P4Schema) -> Any:
    "Decode a StreamMessageResponse to the class registered in _DECODER."

    key = msg.WhichOneof("update")
    if key is None:
        raise ValueError("missing update")

    return _DECODER[key].decode(msg, schema)


# Recursive typedefs.
EntityList = p4r.Entity | _SupportsEncodeEntity | Sequence["EntityList"]
UpdateList = (
    p4r.Update
    | p4r.StreamMessageRequest
    | _SupportsEncodeUpdate
    | Sequence["UpdateList"]
)


def _flatten(values: Any) -> Iterator[Any]:
    "Flatten lists and tuples."
    for val in values:
        if isinstance(val, collections.abc.Sequence):
            yield from _flatten(val)
        else:
            yield val


def _encode_entity(
    value: p4r.Entity | _SupportsEncodeEntity,
    schema: P4Schema,
) -> p4r.Entity:
    "Encode an entity, if necessary."

    if isinstance(value, p4r.Entity):
        return value

    return value.encode(schema)


def encode_entities(values: EntityList, schema: P4Schema) -> list[p4r.Entity]:
    """Convert list of python objects to list of P4Runtime Entities."""

    if not isinstance(values, collections.abc.Sequence):
        return [_encode_entity(values, schema)]

    return [_encode_entity(val, schema) for val in _flatten(values)]


def _encode_update(
    value: p4r.Update | p4r.StreamMessageRequest | _SupportsEncodeUpdate,
    schema: P4Schema,
) -> p4r.Update | p4r.StreamMessageRequest:
    "Encode an Update or outgoing message request, if necessary."

    if isinstance(value, (p4r.Update, p4r.StreamMessageRequest)):
        return value

    return value.encode_update(schema)


def encode_updates(
    values: UpdateList,
    schema: P4Schema,
) -> list[p4r.Update | p4r.StreamMessageRequest]:
    """Convert list of python objects to P4Runtime Updates or request messages."""

    if not isinstance(values, collections.abc.Sequence):
        return [_encode_update(values, schema)]

    return [_encode_update(val, schema) for val in _flatten(values)]


class _Writable:
    _update_type: P4UpdateType = P4UpdateType.UNSPECIFIED

    def __pos__(self):
        self._update_type = P4UpdateType.INSERT
        return self

    def __neg__(self):
        self._update_type = P4UpdateType.DELETE
        return self

    def __invert__(self):
        self._update_type = P4UpdateType.MODIFY
        return self

    def encode(self, _schema: P4Schema) -> p4r.Entity:
        raise NotImplementedError()

    def encode_update(self, schema: P4Schema) -> p4r.Update:
        if self._update_type == P4UpdateType.UNSPECIFIED:
            raise ValueError("unspecified update type")
        return p4r.Update(type=self._update_type.vt(), entity=self.encode(schema))


_DataValueType = Any  # TODO: tighten P4Data type constraint later
_MetadataDictType = dict[str, Any]
_PortType = int
_ReplicaCanonType = tuple[_PortType, int]
_ReplicaType = _ReplicaCanonType | _PortType
_Weight = int | tuple[int, int | bytes]


def encode_replica(value: _ReplicaType) -> p4r.Replica:
    "Convert python representation to Replica."

    if isinstance(value, int):
        egress_port, instance = value, 0
    else:
        assert isinstance(value, tuple) and len(value) == 2
        egress_port, instance = value

    return p4r.Replica(egress_port=egress_port, instance=instance)


def decode_replica(replica: p4r.Replica) -> _ReplicaCanonType:
    "Convert Replica to python representation."

    return (replica.egress_port, replica.instance)


class P4TableMatch(dict[str, Any]):
    "Represents a sequence of P4Runtime FieldMatch."

    def encode(self, table: P4Table) -> list[p4r.FieldMatch]:
        "Encode TableMatch data as protobuf."
        result: list[p4r.FieldMatch] = []
        match_fields = table.match_fields

        for key, value in self.items():
            try:
                field = match_fields[key].encode(value)
                if field is not None:
                    result.append(field)
            except Exception as ex:
                raise ValueError(f"{table.name!r}: Match field {key!r}: {ex}") from ex

        return result

    @classmethod
    def decode(cls, msgs: Sequence[p4r.FieldMatch], table: P4Table) -> Self:
        "Decode protobuf to TableMatch data."
        result = {}
        match_fields = table.match_fields

        for field in msgs:
            fld = match_fields[field.field_id]
            result[fld.alias] = fld.decode(field)

        return cls(result)


@dataclass
class P4TableAction:
    """Represents a P4Runtime Action reference.

    e.g. P4TableAction("ipv4_forward", port=1)
    """

    name: str
    args: dict[str, Any]

    def __init__(self, __name: str, /, **args: Any):
        self.name = __name
        self.args = args

    def encode_table_action(self, table: P4Table) -> p4r.TableAction:
        "Encode TableAction data as protobuf."

        try:
            action = table.actions[self.name]
        except Exception as ex:
            raise ValueError(f"{table.name!r}: {ex}") from ex

        return p4r.TableAction(action=self._encode_action(action))

    def _fail_missing_params(self, action: P4ActionRef | P4Action) -> NoReturn:
        "Report missing parameters."

        seen = {param.name for param in action.params}
        for name in self.args:
            param = action.params[name]
            seen.remove(param.name)

        raise ValueError(f"{action.alias!r}: missing parameters {seen}")

    def encode_action(self, schema: P4Schema) -> p4r.Action:
        "Encode Action data as protobuf."

        # TODO: Make sure that action is normal `Action`.
        action = schema.actions[self.name]
        return self._encode_action(action)

    def _encode_action(self, action: P4ActionRef | P4Action) -> p4r.Action:
        "Helper to encode an action."

        params: list[p4r.Action.Param] = []
        for name, value in self.args.items():
            try:
                param = action.params[name]
                params.append(param.encode(value))
            except ValueError as ex:
                raise ValueError(f"{action.alias!r}: {ex}") from ex

        # Check for missing action parameters.
        if len(params) != len(action.params):
            self._fail_missing_params(action)

        return p4r.Action(action_id=action.id, params=params)

    @classmethod
    def decode_table_action(cls, msg: p4r.TableAction, table: P4Table) -> Self:
        "Decode protobuf to TableAction data."

        match msg.WhichOneof("type"):
            case "action":
                return cls.decode_action(msg.action, table)
            case "action_profile_member_id":
                raise NotImplementedError()
            case "action_profile_group_id":
                raise NotImplementedError()
            case "action_profile_action_set":
                raise NotImplementedError()
            case other:
                raise ValueError(f"unknown oneof: {other!r}")

    @classmethod
    def decode_action(cls, msg: p4r.Action, parent: P4Schema | P4Table) -> Self:
        "Decode protobuf to Action data."

        action = parent.actions[msg.action_id]
        args = {}
        for param in msg.params:
            action_param = action.params[param.param_id]
            value = action_param.decode(param)
            args[action_param.name] = value

        return cls(action.alias, **args)


@dataclass(kw_only=True)
class P4MeterConfig:
    "Represents a P4Runtime MeterConfig."

    cir: int
    cburst: int
    pir: int
    pburst: int

    def encode(self) -> p4r.MeterConfig:
        return p4r.MeterConfig(**self.__dict__)

    @classmethod
    def decode(cls, msg: p4r.MeterConfig) -> Self:
        return cls(cir=msg.cir, cburst=msg.cburst, pir=msg.pir, pburst=msg.pburst)


@dataclass(kw_only=True)
class P4CounterData:
    "Represents a P4Runtime CounterData."

    byte_count: int
    packet_count: int

    def encode(self) -> p4r.CounterData:
        return p4r.CounterData(**self.__dict__)

    @classmethod
    def decode(cls, msg: p4r.CounterData) -> Self:
        return cls(byte_count=msg.byte_count, packet_count=msg.packet_count)


@dataclass(kw_only=True)
class P4MeterCounterData:
    "Represents a P4Runtime MeterCounterData."

    green: P4CounterData
    yellow: P4CounterData
    red: P4CounterData

    def encode(self) -> p4r.MeterCounterData:
        return p4r.MeterCounterData(
            green=self.green.encode(),
            yellow=self.yellow.encode(),
            red=self.red.encode(),
        )

    @classmethod
    def decode(cls, msg: p4r.MeterCounterData) -> Self:
        return cls(
            green=P4CounterData.decode(msg.green),
            yellow=P4CounterData.decode(msg.yellow),
            red=P4CounterData.decode(msg.red),
        )


@decodable("table_entry")
@dataclass
class P4TableEntry(_Writable):
    "Represents a P4Runtime TableEntry."

    table_id: str = ""
    _: KW_ONLY
    match: P4TableMatch | None = None
    action: P4TableAction | None = None
    priority: int = 0
    meter_config: P4MeterConfig | None = None
    counter_data: P4CounterData | None = None
    meter_counter_data: P4MeterCounterData | None = None
    is_default_action: bool = False
    idle_timeout_ns: int = 0
    time_since_last_hit: int | None = None
    metadata: bytes = b""

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode TableEntry data as protobuf."

        return p4r.Entity(table_entry=self.encode_entry(schema))

    def encode_entry(self, schema: P4Schema) -> p4r.TableEntry:
        "Encode TableEntry data as protobuf."

        if not self.table_id:
            return p4r.TableEntry()

        table = schema.tables[self.table_id]

        if self.match:
            match = self.match.encode(table)
        else:
            match = None

        if self.action:
            action = self.action.encode_table_action(table)
        else:
            action = None

        if self.meter_config:
            meter_config = self.meter_config.encode()
        else:
            meter_config = None

        if self.counter_data:
            counter_data = self.counter_data.encode()
        else:
            counter_data = None

        if self.meter_counter_data:
            meter_counter_data = self.meter_counter_data.encode()
        else:
            meter_counter_data = None

        if self.time_since_last_hit is not None:
            time_since_last_hit = p4r.TableEntry.IdleTimeout(
                elapsed_ns=self.time_since_last_hit
            )
        else:
            time_since_last_hit = None

        return p4r.TableEntry(
            table_id=table.id,
            match=match,
            action=action,
            priority=self.priority,
            meter_config=meter_config,
            counter_data=counter_data,
            meter_counter_data=meter_counter_data,
            is_default_action=self.is_default_action,
            idle_timeout_ns=self.idle_timeout_ns,
            time_since_last_hit=time_since_last_hit,
            metadata=self.metadata,
        )

    @classmethod
    def decode(cls, msg: p4r.Entity, schema: P4Schema) -> Self:
        "Decode protobuf to TableEntry data."

        return cls.decode_entry(msg.table_entry, schema)

    @classmethod
    def decode_entry(cls, entry: p4r.TableEntry, schema: P4Schema) -> Self:
        "Decode protobuf to TableEntry data."

        if entry.table_id == 0:
            return cls("")

        table = schema.tables[entry.table_id]

        if entry.match:
            match = P4TableMatch.decode(entry.match, table)
        else:
            match = None

        if entry.HasField("action"):
            action = P4TableAction.decode_table_action(entry.action, table)
        else:
            action = None

        if entry.HasField("time_since_last_hit"):
            last_hit = entry.time_since_last_hit.elapsed_ns
        else:
            last_hit = None

        if entry.HasField("meter_config"):
            meter_config = P4MeterConfig.decode(entry.meter_config)
        else:
            meter_config = None

        # TODO: More fields.

        return cls(
            table_id=table.alias,
            match=match,
            action=action,
            priority=entry.priority,
            meter_config=meter_config,
            is_default_action=entry.is_default_action,
            idle_timeout_ns=entry.idle_timeout_ns,
            time_since_last_hit=last_hit,
            metadata=entry.metadata,
        )


@decodable("register_entry")
@dataclass
class P4RegisterEntry(_Writable):
    "Represents a P4Runtime RegisterEntry."

    register_id: str = ""
    _: KW_ONLY
    index: int | None = None
    data: _DataValueType | None = None

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode RegisterEntry data as protobuf."

        if not self.register_id:
            return p4r.Entity(register_entry=p4r.RegisterEntry())

        register = schema.registers[self.register_id]

        if self.index is not None:
            index = p4r.Index(index=self.index)
        else:
            index = None

        if self.data is not None:
            data = register.type_spec.encode_data(self.data)
        else:
            data = None

        entry = p4r.RegisterEntry(
            register_id=register.id,
            index=index,
            data=data,
        )
        return p4r.Entity(register_entry=entry)

    @classmethod
    def decode(cls, msg: p4r.Entity, schema: P4Schema) -> Self:
        "Decode protobuf to RegisterEntry data."

        entry = msg.register_entry
        if entry.register_id == 0:
            return cls("")

        register = schema.registers[entry.register_id]

        if entry.HasField("index"):
            index = entry.index.index
        else:
            index = None

        if entry.HasField("data"):
            data = register.type_spec.decode_data(entry.data)
        else:
            data = None

        return cls(
            register.alias,
            index=index,
            data=data,
        )


@decodable("multicast_group_entry")
@dataclass
class P4MulticastGroupEntry(_Writable):
    "Represents a P4Runtime MulticastGroupEntry."

    multicast_group_id: int = 0
    _: KW_ONLY
    replicas: Sequence[_ReplicaType] = ()

    def encode(self, _schema: P4Schema) -> p4r.Entity:
        "Encode MulticastGroupEntry data as protobuf."

        entry = p4r.MulticastGroupEntry(
            multicast_group_id=self.multicast_group_id,
            replicas=[encode_replica(replica) for replica in self.replicas],
        )
        return p4r.Entity(
            packet_replication_engine_entry=p4r.PacketReplicationEngineEntry(
                multicast_group_entry=entry
            )
        )

    @classmethod
    def decode(cls, msg: p4r.Entity, _schema: P4Schema) -> Self:
        "Decode protobuf to MulticastGroupEntry data."

        entry = msg.packet_replication_engine_entry.multicast_group_entry
        return cls(
            multicast_group_id=entry.multicast_group_id,
            replicas=tuple(decode_replica(replica) for replica in entry.replicas),
        )


@decodable("clone_session_entry")
@dataclass
class P4CloneSessionEntry(_Writable):
    "Represents a P4Runtime CloneSessionEntry."

    session_id: int = 0
    _: KW_ONLY
    class_of_service: int = 0
    packet_length_bytes: int = 0
    replicas: Sequence[_ReplicaType] = ()

    def encode(self, _schema: P4Schema) -> p4r.Entity:
        "Encode CloneSessionEntry data as protobuf."

        entry = p4r.CloneSessionEntry(
            session_id=self.session_id,
            class_of_service=self.class_of_service,
            packet_length_bytes=self.packet_length_bytes,
            replicas=[encode_replica(replica) for replica in self.replicas],
        )
        return p4r.Entity(
            packet_replication_engine_entry=p4r.PacketReplicationEngineEntry(
                clone_session_entry=entry
            )
        )

    @classmethod
    def decode(cls, msg: p4r.Entity, _schema: P4Schema) -> Self:
        "Decode protobuf to CloneSessionEntry data."

        entry = msg.packet_replication_engine_entry.clone_session_entry
        return cls(
            session_id=entry.session_id,
            class_of_service=entry.class_of_service,
            packet_length_bytes=entry.packet_length_bytes,
            replicas=tuple(decode_replica(replica) for replica in entry.replicas),
        )


@decodable("digest_entry")
@dataclass
class P4DigestEntry(_Writable):
    "Represents a P4Runtime DigestEntry."

    digest_id: str
    _: KW_ONLY
    max_list_size: int = 0
    max_timeout_ns: int = 0
    ack_timeout_ns: int = 0

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode DigestEntry data as protobuf."
        digest = schema.digests[self.digest_id]

        if self.max_list_size == self.max_timeout_ns == self.ack_timeout_ns == 0:
            config = None
        else:
            config = p4r.DigestEntry.Config(
                max_timeout_ns=self.max_timeout_ns,
                max_list_size=self.max_list_size,
                ack_timeout_ns=self.ack_timeout_ns,
            )

        entry = p4r.DigestEntry(digest_id=digest.id, config=config)
        return p4r.Entity(digest_entry=entry)

    @classmethod
    def decode(cls, msg: p4r.Entity, schema: P4Schema) -> Self:
        "Decode protobuf to DigestEntry data."
        entry = msg.digest_entry
        digest = schema.digests[entry.digest_id]

        config = entry.config
        return cls(
            digest.alias,
            max_list_size=config.max_list_size,
            max_timeout_ns=config.max_timeout_ns,
            ack_timeout_ns=config.ack_timeout_ns,
        )


@decodable("action_profile_member")
@dataclass
class P4ActionProfileMember(_Writable):
    "Represents a P4Runtime ActionProfileMember."

    action_profile_id: int = 0
    _: KW_ONLY
    member_id: int = 0
    action: P4TableAction | None = None

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode P4ActionProfileMember as protobuf."

        if self.action:
            action = self.action.encode_action(schema)
        else:
            action = None

        entry = p4r.ActionProfileMember(
            action_profile_id=self.action_profile_id,
            member_id=self.member_id,
            action=action,
        )
        return p4r.Entity(action_profile_member=entry)

    @classmethod
    def decode(cls, msg: p4r.Entity, schema: P4Schema) -> Self:
        "Decode protobuf to ActionProfileMember data."
        entry = msg.action_profile_member

        if entry.HasField("action"):
            action = P4TableAction.decode_action(entry.action, schema)
        else:
            action = None

        return cls(
            action_profile_id=entry.action_profile_id,
            member_id=entry.member_id,
            action=action,
        )


@dataclass(kw_only=True)
class P4Member:
    "Represents an ActionProfileGroup Member."

    member_id: int
    weight: _Weight

    def encode(self) -> p4r.ActionProfileGroup.Member:
        "Encode P4Member as protobuf."

        watch = None
        watch_port = None

        match self.weight:
            case int(weight):
                pass
            case (int(weight), int(watch)):
                pass
            case (int(weight), bytes(watch_port)):
                pass
            case other:
                raise ValueError(f"unexpected weight: {other!r}")

        member = p4r.ActionProfileGroup.Member(
            member_id=self.member_id,
            weight=weight,
        )

        if watch is not None:
            member.watch = watch
        elif watch_port is not None:
            member.watch_port = watch_port

        return member

    @classmethod
    def decode(cls, msg: p4r.ActionProfileGroup.Member) -> Self:
        "Decode protobuf to P4Member."

        match msg.WhichOneof("watch_kind"):
            case "watch":
                weight = (msg.weight, msg.watch)
            case "watch_port":
                weight = (msg.weight, msg.watch_port)
            case other:
                raise ValueError(f"unknown oneof: {other!r}")

        return cls(member_id=msg.member_id, weight=weight)


@decodable("action_profile_group")
@dataclass
class P4ActionProfileGroup(_Writable):
    "Represents a P4Runtime ActionProfileGroup."

    action_profile_id: int = 0
    _: KW_ONLY
    group_id: int = 0
    max_size: int = 0
    members: Sequence[P4Member] | None = None

    def encode(self, _schema: P4Schema) -> p4r.Entity:
        "Encode P4ActionProfileGroup as protobuf."

        if self.members is not None:
            members = [member.encode() for member in self.members]
        else:
            members = None

        entry = p4r.ActionProfileGroup(
            action_profile_id=self.action_profile_id,
            group_id=self.group_id,
            members=members,
            max_size=self.max_size,
        )
        return p4r.Entity(action_profile_group=entry)

    @classmethod
    def decode(cls, msg: p4r.Entity, _schema: P4Schema) -> Self:
        "Decode protobuf to ActionProfileGroup data."
        entry = msg.action_profile_group

        if entry.members:
            members = [P4Member.decode(member) for member in entry.members]
        else:
            members = None

        return cls(
            action_profile_id=entry.action_profile_id,
            group_id=entry.group_id,
            max_size=entry.max_size,
            members=members,
        )


@decodable("meter_entry")
@dataclass
class P4MeterEntry(_Writable):
    "Represents a P4Runtime MeterEntry."

    meter_id: int = 0
    _: KW_ONLY
    index: int | None = None
    config: P4MeterConfig | None = None
    counter_data: P4MeterCounterData | None = None

    def encode(self, _schema: P4Schema) -> p4r.Entity:
        "Encode P4MeterEntry to protobuf."

        if self.index is not None:
            index = p4r.Index(index=self.index)
        else:
            index = None

        if self.config is not None:
            config = self.config.encode()
        else:
            config = None

        if self.counter_data is not None:
            counter_data = self.counter_data.encode()
        else:
            counter_data = None

        entry = p4r.MeterEntry(
            meter_id=self.meter_id,
            index=index,
            config=config,
            counter_data=counter_data,
        )
        return p4r.Entity(meter_entry=entry)

    @classmethod
    def decode(cls, msg: p4r.Entity, _schema: P4Schema) -> Self:
        "Decode protobuf to P4MeterEntry."

        entry = msg.meter_entry

        if entry.HasField("index"):
            index = entry.index.index
        else:
            index = None

        if entry.HasField("config"):
            config = P4MeterConfig.decode(entry.config)
        else:
            config = None

        if entry.HasField("counter_data"):
            counter_data = P4MeterCounterData.decode(entry.counter_data)
        else:
            counter_data = None

        return cls(
            meter_id=entry.meter_id,
            index=index,
            config=config,
            counter_data=counter_data,
        )


@decodable("direct_meter_entry")
@dataclass
class P4DirectMeterEntry(_Writable):
    "Represents a P4Runtime DirectMeterEntry."

    table_entry: P4TableEntry | None = None
    _: KW_ONLY
    config: P4MeterConfig | None = None
    counter_data: P4MeterCounterData | None = None

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode P4DirectMeterEntry as protobuf."

        if self.table_entry is not None:
            table_entry = self.table_entry.encode_entry(schema)
        else:
            table_entry = p4r.TableEntry()

        if self.config is not None:
            config = self.config.encode()
        else:
            config = None

        if self.counter_data is not None:
            counter_data = self.counter_data.encode()
        else:
            counter_data = None

        entry = p4r.DirectMeterEntry(
            table_entry=table_entry,
            config=config,
            counter_data=counter_data,
        )
        return p4r.Entity(direct_meter_entry=entry)

    @classmethod
    def decode(cls, msg: p4r.Entity, schema: P4Schema) -> Self:
        "Decode protobuf to P4DirectMeterEntry."

        entry = msg.direct_meter_entry
        table_entry = P4TableEntry.decode_entry(entry.table_entry, schema)

        if entry.HasField("config"):
            config = P4MeterConfig.decode(entry.config)
        else:
            config = None

        if entry.HasField("counter_data"):
            counter_data = P4MeterCounterData.decode(entry.counter_data)
        else:
            counter_data = None

        return cls(
            table_entry=table_entry,
            config=config,
            counter_data=counter_data,
        )


@decodable("counter_entry")
@dataclass
class P4CounterEntry(_Writable):
    "Represents a P4Runtime CounterEntry."

    counter_id: int = 0
    _: KW_ONLY
    index: int | None = None
    data: P4CounterData | None = None

    def encode(self, _schema: P4Schema) -> p4r.Entity:
        "Encode P4CounterEntry as protobuf."

        if self.index is not None:
            index = p4r.Index(index=self.index)
        else:
            index = None

        if self.data is not None:
            data = self.data.encode()
        else:
            data = None

        entry = p4r.CounterEntry(
            counter_id=self.counter_id,
            index=index,
            data=data,
        )
        return p4r.Entity(counter_entry=entry)

    @classmethod
    def decode(cls, msg: p4r.Entity, _schema: P4Schema) -> Self:
        "Decode protobuf to P4CounterEntry."

        entry = msg.counter_entry

        if entry.HasField("index"):
            index = entry.index.index
        else:
            index = None

        if entry.HasField("data"):
            data = P4CounterData.decode(entry.data)
        else:
            data = None

        return cls(counter_id=entry.counter_id, index=index, data=data)


@decodable("direct_counter_entry")
@dataclass
class P4DirectCounterEntry(_Writable):
    "Represents a P4Runtime DirectCounterEntry."

    table_entry: P4TableEntry | None = None
    _: KW_ONLY
    data: P4CounterData | None = None

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode P4DirectCounterEntry as protobuf."

        if self.table_entry is not None:
            table_entry = self.table_entry.encode_entry(schema)
        else:
            table_entry = None

        if self.data is not None:
            data = self.data.encode()
        else:
            data = None

        entry = p4r.DirectCounterEntry(
            table_entry=table_entry,
            data=data,
        )
        return p4r.Entity(direct_counter_entry=entry)

    @classmethod
    def decode(cls, msg: p4r.Entity, schema: P4Schema) -> Self:
        "Decode protobuf to P4DirectCounterEntry."

        entry = msg.direct_counter_entry

        if entry.HasField("table_entry"):
            table_entry = P4TableEntry.decode_entry(entry.table_entry, schema)
        else:
            table_entry = None

        if entry.HasField("data"):
            data = P4CounterData.decode(entry.data)
        else:
            data = None

        return cls(table_entry=table_entry, data=data)


@decodable("packet")
@dataclass
class P4PacketIn:
    "Represents a P4Runtime PacketIn."

    payload: bytes
    _: KW_ONLY
    metadata: _MetadataDictType

    @classmethod
    def decode(cls, msg: p4r.StreamMessageResponse, schema: P4Schema) -> Self:
        "Decode protobuf to PacketIn data."

        packet = msg.packet
        cpm = schema.controller_packet_metadata.get("packet_in")
        if cpm is None:
            # There is no controller metadata. Warn if message has any.
            if packet.HasField("metadata"):
                LOGGER.warning("unexpected metadata: %r", packet.metadata)
            return cls(packet.payload, metadata={})

        return cls(
            packet.payload,
            metadata=cpm.decode(packet.metadata),
        )

    def __getitem__(self, key: str):
        "Retrieve metadata value."

        return self.metadata[key]

    def __repr__(self):
        "Return friendlier hexadecimal description of packet."

        if self.metadata:
            return (
                f"PacketIn(metadata={self.metadata!r}, payload=h'{self.payload.hex()}')"
            )
        return f"PacketIn(payload=h'{self.payload.hex()}')"


@dataclass
class P4PacketOut:
    "Represents a P4Runtime PacketOut."

    payload: bytes
    metadata: _MetadataDictType

    def __init__(self, __payload: bytes, /, **metadata: Any):
        self.payload = __payload
        self.metadata = metadata

    def encode_update(self, schema: P4Schema) -> p4r.StreamMessageRequest:
        "Encode PacketOut data as protobuf."

        cpm = schema.controller_packet_metadata["packet_out"]
        return p4r.StreamMessageRequest(
            packet=p4r.PacketOut(
                payload=self.payload,
                metadata=cpm.encode(self.metadata),
            )
        )

    def __getitem__(self, key: str):
        "Retrieve metadata value."

        return self.metadata[key]

    def __repr__(self):
        "Return friendlier hexadecimal description of packet."

        if self.metadata:
            return f"PacketOut(metadata={self.metadata!r}, payload=h'{self.payload.hex()}')"
        return f"PacketOut(payload=h'{self.payload.hex()}')"


@decodable("digest")
@dataclass
class P4DigestList:
    "Represents a P4Runtime DigestList."

    digest_id: str
    _: KW_ONLY
    list_id: int
    timestamp: int
    data: list[_DataValueType]

    @classmethod
    def decode(cls, msg: p4r.StreamMessageResponse, schema: P4Schema) -> Self:
        "Decode protobuf to DigestList data."

        digest_list = msg.digest
        digest = schema.digests[digest_list.digest_id]

        type_spec = digest.type_spec
        return cls(
            digest_id=digest.alias,
            list_id=digest_list.list_id,
            timestamp=digest_list.timestamp,
            data=[type_spec.decode_data(item) for item in digest_list.data],
        )

    def __len__(self):
        "Return number of values in digest list."
        return len(self.data)

    def __getitem__(self, key: int):
        "Retrieve value at given index from digest list."
        return self.data[key]

    def __iter__(self):
        "Iterate over values in digest list."
        return iter(self.data)


@dataclass
class P4DigestListAck:
    "Represents a P4Runtime DigestListAck."


@decodable("idle_timeout_notification")
@dataclass
class P4IdleTimeoutNotification:
    "Represents a P4Runtime IdleTimeoutNotification."
