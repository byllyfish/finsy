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
from typing import Any, Sequence

from typing_extensions import Self

from finsy.log import LOGGER
from finsy.p4schema import P4ActionRef, P4Schema, P4Table, P4UpdateType
from finsy.proto import p4r

_DECODE_ENTITY = {}
_DECODE_STREAM = {}


def decodable(msg_class, *keys: str):
    "Decorator to specify the class used to decode various P4Runtime messages."

    def _decorate(cls):
        if msg_class is p4r.Entity:
            table1 = _DECODE_ENTITY
        elif msg_class is p4r.StreamMessageResponse:
            table1 = _DECODE_STREAM
        else:
            raise ValueError(f"unexpected msg_class: {msg_class!r}")

        match keys:
            case (key1,):
                table1[key1] = cls
            case (key1, key2):
                table2 = table1.setdefault(key1, {})
                table2[key2] = cls
            case _:
                raise ValueError(f"unexpected keys: {keys!r}")

        return cls

    return _decorate


def decode_entity(msg: p4r.Entity, schema: P4Schema) -> Any:
    key = msg.WhichOneof("entity")
    if key is None:
        raise ValueError(f"unexpected entity: {msg!r}")

    cls = _DECODE_ENTITY[key]
    if isinstance(cls, dict):
        submsg = getattr(msg, key)
        assert isinstance(submsg, p4r.PacketReplicationEngineEntry)
        cls = cls[submsg.WhichOneof("type")]
    return cls.decode(msg, schema)


def decode_stream(msg: p4r.StreamMessageResponse, schema: P4Schema) -> Any:
    key = msg.WhichOneof("update")
    cls = _DECODE_STREAM[key]
    return cls.decode(msg, schema)


def _flatten(values):
    "Flatten lists and tuples."
    for val in values:
        if isinstance(val, collections.abc.Sequence):
            yield from _flatten(val)
        else:
            yield val


def _encode_entity(value, schema):
    "Encode an entity, if necessary."

    if isinstance(value, p4r.Entity):
        return value
    return value.encode(schema)


def encode_entities(values, schema: P4Schema) -> list[p4r.Entity]:
    """Convert list of python objects to list of P4Runtime Entities.

    Note: The list is flattened.
    """

    if not isinstance(values, collections.abc.Sequence):
        return [_encode_entity(values, schema)]

    return [_encode_entity(val, schema) for val in _flatten(values)]


def _encode_update(value, schema):
    "Encode an Update or outgoing message request, if necessary."

    if isinstance(value, (p4r.Update, p4r.StreamMessageRequest)):
        return value
    return value.encode_update(schema)


def encode_updates(
    values, schema: P4Schema
) -> list[p4r.Update | p4r.StreamMessageRequest]:
    """Convert list of python objects to P4Runtime Update's or stream messages."""

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
        result = []
        match_fields = table.match_fields

        for key, value in self.items():
            try:
                result.append(match_fields[key].encode(value))
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

    e.g. TableAction("ipv4_forward", port=1)
    """

    name: str
    args: dict[str, Any]

    def __init__(self, __name, /, **args):
        self.name = __name
        self.args = args

    def encode(self, table: P4Table) -> p4r.TableAction:
        "Encode TableAction data as protobuf."

        try:
            action = table.actions[self.name]
        except Exception as ex:
            raise ValueError(f"{table.name!r}: {ex}") from ex

        params = []
        for name, value in self.args.items():
            try:
                param = action.params[name]
                params.append(param.encode(value))
            except ValueError as ex:
                raise ValueError(f"{table.name!r}: {action.alias!r}: {ex}") from ex

        # Check for missing action parameters.
        if len(params) != len(action.params):
            self._fail_missing_params(table, action)

        return p4r.TableAction(action=p4r.Action(action_id=action.id, params=params))

    def _fail_missing_params(self, table: P4Table, action: P4ActionRef):
        "Report missing parameters."
        seen = {param.name for param in action.params}

        for name in self.args:
            param = action.params[name]
            seen.remove(param.name)

        raise ValueError(f"{table.name!r}: {action.alias!r}: missing parameters {seen}")

    @classmethod
    def decode(cls, msg: p4r.TableAction, table: P4Table) -> Self:
        "Decode protobuf to TableAction data."

        match msg.WhichOneof("type"):
            case "action":
                return cls._decode_action(msg.action, table)
            case "action_profile_member_id":
                raise NotImplementedError()
            case "action_profile_group_id":
                raise NotImplementedError()
            case "action_profile_action_set":
                raise NotImplementedError()
            case other:
                raise ValueError(f"unknown oneof: {other!r}")

    @classmethod
    def _decode_action(cls, msg: p4r.Action, table: P4Table) -> Self:
        "Decode protobuf action."
        action = table.actions[msg.action_id]
        name = action.alias

        args = {}
        for param in msg.params:
            action_param = action.params[param.param_id]
            value = action_param.decode(param)
            args[action_param.name] = value

        return cls(name, **args)


@dataclass(kw_only=True)
class P4MeterConfig:
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
    byte_count: int
    packet_count: int

    def encode(self) -> p4r.CounterData:
        return p4r.CounterData(**self.__dict__)

    @classmethod
    def decode(cls, msg: p4r.CounterData) -> Self:
        return cls(byte_count=msg.byte_count, packet_count=msg.packet_count)


@dataclass(kw_only=True)
class P4MeterCounterData:
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


@decodable(p4r.Entity, "table_entry")
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

        if not self.table_id:
            return p4r.Entity(table_entry=p4r.TableEntry())

        table = schema.tables[self.table_id]

        if self.match:
            match = self.match.encode(table)
        else:
            match = None

        if self.action:
            action = self.action.encode(table)
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

        return p4r.Entity(
            table_entry=p4r.TableEntry(
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
        )

    @classmethod
    def decode(cls, msg: p4r.Entity, schema: P4Schema) -> Self:
        "Decode protobuf to TableEntry data."

        entry = msg.table_entry
        if entry.table_id == 0:
            return cls("")

        table = schema.tables[entry.table_id]

        if entry.match:
            match = P4TableMatch.decode(entry.match, table)
        else:
            match = None

        if entry.HasField("action"):
            action = P4TableAction.decode(entry.action, table)
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


@decodable(p4r.Entity, "register_entry")
@dataclass
class P4RegisterEntry(_Writable):
    "Represents a P4Runtime RegisterEntry."

    register_id: str
    _: KW_ONLY
    index: int | None = None
    data: _DataValueType | None = None

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode RegisterEntry data as protobuf."
        assert self.data is not None

        register = schema.registers[self.register_id]
        index = p4r.Index(index=self.index) if self.index is not None else None
        entry = p4r.RegisterEntry(
            register_id=register.id,
            index=index,
            data=register.type_spec.encode_data(self.data),
        )
        return p4r.Entity(register_entry=entry)

    @classmethod
    def decode(cls, msg: p4r.Entity, schema: P4Schema) -> Self:
        "Decode protobuf to RegisterEntry data."

        entry = msg.register_entry
        register = schema.registers[entry.register_id]
        index = entry.index.index if entry.HasField("index") else None
        return cls(
            register.alias,
            index=index,
            data=register.type_spec.decode_data(entry.data),
        )


@decodable(p4r.Entity, "packet_replication_engine_entry", "multicast_group_entry")
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
            replicas=[decode_replica(replica) for replica in entry.replicas],
        )


@decodable(p4r.Entity, "digest_entry")
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


@decodable(p4r.StreamMessageResponse, "packet")
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

    def __getitem__(self, key):
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

    def __init__(self, __payload: bytes, /, **metadata):
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

    def __getitem__(self, key):
        "Retrieve metadata value."

        return self.metadata[key]

    def __repr__(self):
        "Return friendlier hexadecimal description of packet."

        if self.metadata:
            return f"PacketOut(metadata={self.metadata!r}, payload=h'{self.payload.hex()}')"
        return f"PacketOut(payload=h'{self.payload.hex()}')"


@decodable(p4r.StreamMessageResponse, "digest")
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

    def __getitem__(self, key):
        "Retrieve value at given index from digest list."
        return self.data[key]

    def __iter__(self):
        "Iterate over values in digest list."
        return iter(self.data)
