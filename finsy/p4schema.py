"Support for P4Info files."

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

import hashlib
import inspect
import re
from pathlib import Path
from typing import Any, Generic, Iterator, NamedTuple, SupportsBytes, TypeVar

import pylev

import finsy.pbuf as pbuf
import finsy.values as values
from finsy.grpcutil import GRPCStatusCode, _EnumBase
from finsy.proto import p4d, p4i, p4r, p4t, rpc_code

# Enums
# ~~~~~
#
# Wrap protobuf enums with Python Enums. This gives better runtime type
# checking and a useful __repr__.
#
# We write out the members here to retain typing/autocomplete support from the
# IDE. We assert that our enum classes have the same members as the
# associated protobuf enum.


class P4MatchType(_EnumBase):
    "IntEnum equivalent to `p4i.MatchField.MatchType`."
    UNSPECIFIED = p4i.MatchField.MatchType.UNSPECIFIED
    EXACT = p4i.MatchField.MatchType.EXACT
    LPM = p4i.MatchField.MatchType.LPM
    TERNARY = p4i.MatchField.MatchType.TERNARY
    RANGE = p4i.MatchField.MatchType.RANGE
    OPTIONAL = p4i.MatchField.MatchType.OPTIONAL


class P4IdleTimeoutBehavior(_EnumBase):
    "IntEnum equivalent to `p4i.Table.IdleTimeoutBehavior`."
    NO_TIMEOUT = p4i.Table.IdleTimeoutBehavior.NO_TIMEOUT
    NOTIFY_CONTROL = p4i.Table.IdleTimeoutBehavior.NOTIFY_CONTROL


class P4ActionScope(_EnumBase):
    "IntEnum equivalent to `p4i.Table.IdleTimeoutBehavior`."
    TABLE_AND_DEFAULT = p4i.ActionRef.Scope.TABLE_AND_DEFAULT
    TABLE_ONLY = p4i.ActionRef.Scope.TABLE_ONLY
    DEFAULT_ONLY = p4i.ActionRef.Scope.DEFAULT_ONLY


class P4CounterUnit(_EnumBase):
    "IntEnum equivalent to `p4i.CounterSpec.Unit`."
    UNSPECIFIED = p4i.CounterSpec.Unit.UNSPECIFIED
    BYTES = p4i.CounterSpec.Unit.BYTES
    PACKETS = p4i.CounterSpec.Unit.PACKETS
    BOTH = p4i.CounterSpec.Unit.BOTH


class P4MeterUnit(_EnumBase):
    "IntEnum equivalent to `p4i.MeterSpec.Unit`."
    UNSPECIFIED = p4i.MeterSpec.Unit.UNSPECIFIED
    BYTES = p4i.MeterSpec.Unit.BYTES
    PACKETS = p4i.MeterSpec.Unit.PACKETS


class P4ConfigResponseType(_EnumBase):
    "IntEnum equivalent to `p4r.GetForwardingPipelineConfigRequest.ResponseType`."
    ALL = p4r.GetForwardingPipelineConfigRequest.ResponseType.ALL
    COOKIE_ONLY = p4r.GetForwardingPipelineConfigRequest.ResponseType.COOKIE_ONLY
    P4INFO_AND_COOKIE = (
        p4r.GetForwardingPipelineConfigRequest.ResponseType.P4INFO_AND_COOKIE
    )
    DEVICE_CONFIG_AND_COOKIE = (
        p4r.GetForwardingPipelineConfigRequest.ResponseType.DEVICE_CONFIG_AND_COOKIE
    )


class P4ConfigAction(_EnumBase):
    "IntEnum equivalent to `p4r.SetForwardingPipelineConfigRequest.Action`."
    UNSPECIFIED = p4r.SetForwardingPipelineConfigRequest.Action.UNSPECIFIED
    VERIFY = p4r.SetForwardingPipelineConfigRequest.Action.VERIFY
    VERIFY_AND_SAVE = p4r.SetForwardingPipelineConfigRequest.Action.VERIFY_AND_SAVE
    VERIFY_AND_COMMIT = p4r.SetForwardingPipelineConfigRequest.Action.VERIFY_AND_COMMIT
    COMMIT = p4r.SetForwardingPipelineConfigRequest.Action.COMMIT
    RECONCILE_AND_COMMIT = (
        p4r.SetForwardingPipelineConfigRequest.Action.RECONCILE_AND_COMMIT
    )


class P4Atomicity(_EnumBase):
    "IntEnum equivalent to `p4r.WriteRequest.Atomicity`."
    CONTINUE_ON_ERROR = p4r.WriteRequest.Atomicity.CONTINUE_ON_ERROR
    ROLLBACK_ON_ERROR = p4r.WriteRequest.Atomicity.ROLLBACK_ON_ERROR
    DATAPLANE_ATOMIC = p4r.WriteRequest.Atomicity.DATAPLANE_ATOMIC


class P4UpdateType(_EnumBase):
    "IntEnum equivalent to `p4r.Update.Type`."
    UNSPECIFIED = p4r.Update.Type.UNSPECIFIED
    INSERT = p4r.Update.Type.INSERT
    DELETE = p4r.Update.Type.DELETE
    MODIFY = p4r.Update.Type.MODIFY


def _validate_enum(enum_class, pbuf_class):
    "Verify that our enum class contains the same members as the protobuf."
    for name, value in pbuf_class.items():
        try:
            enum_value = enum_class[name].value
        except KeyError:
            enum_value = None
        assert enum_value == value, f"Enum {enum_class.__name__!r} missing {name!r}"


# Verify that enum convenience classes have the same members as the protobuf
# classes.

_validate_enum(P4MatchType, p4i.MatchField.MatchType)
_validate_enum(P4IdleTimeoutBehavior, p4i.Table.IdleTimeoutBehavior)
_validate_enum(P4ActionScope, p4i.ActionRef.Scope)
_validate_enum(P4CounterUnit, p4i.CounterSpec.Unit)
_validate_enum(P4MeterUnit, p4i.MeterSpec.Unit)
_validate_enum(
    P4ConfigResponseType,
    p4r.GetForwardingPipelineConfigRequest.ResponseType,
)
_validate_enum(P4ConfigAction, p4r.SetForwardingPipelineConfigRequest.Action)
_validate_enum(P4Atomicity, p4r.WriteRequest.Atomicity)
_validate_enum(P4UpdateType, p4r.Update.Type)
_validate_enum(GRPCStatusCode, rpc_code.Code)


# Base Classes
# ~~~~~~~~~~~~


class _ReprMixin:
    """Mixin class to implement a generic __repr__ method.

    Output only includes explicit object properties (using @property).
    Property values that are redundant or verbose are exempt.
    """

    def __repr__(self):
        EXEMPT_PROPERTIES = {"pbuf", "p4info", "p4blob"}

        cls = type(self)
        properties = [
            name
            for (name, _) in inspect.getmembers(cls, inspect.isdatadescriptor)
            if not name.startswith("_") and name not in EXEMPT_PROPERTIES
        ]

        attrs = [f"{name}={getattr(self, name)!r}" for name in properties]
        return f"{cls.__name__}({', '.join(attrs)})"


_T = TypeVar("_T")


class _P4Bridged(_ReprMixin, Generic[_T]):
    """Generic base class that wraps a corresponding protobuf message <T>.

    You can access the protobuf using the `.pbuf` property.
    """

    def __init__(self, pbuf: _T):
        self.pbuf = pbuf
        "Corresponding protobuf message."


class _P4AnnoMixin:
    """Mixin class for entities and sub-entities that have annotations.

    Overrides __init__. Must be placed first.
    """

    def __init__(self, pbuf):
        super().__init__(pbuf)  # pyright: ignore
        self._annotations = _parse_annotations(pbuf)

    @property
    def annotations(self) -> list["P4Annotation"]:
        "Annotations associated with the entity."
        return self._annotations


class _P4DocMixin:
    "Mixin class for sub-entities that have descriptions."

    @property
    def brief(self):
        return self.pbuf.doc.brief  # type: ignore[attr-defined]

    @property
    def description(self):
        return self.pbuf.doc.description  # type: ignore[attr-defined]


class _P4TopLevel(_P4AnnoMixin, _P4Bridged[_T]):
    """Generic base class for entities at the top level of the P4Info file."""

    @property
    def id(self) -> int:
        "Entity ID."
        return self.pbuf.preamble.id  # type: ignore[attr-defined]

    @property
    def name(self) -> str:
        "Entity name."
        return self.pbuf.preamble.name  # type: ignore[attr-defined]

    @property
    def alias(self) -> str:
        "Entity alias."
        return self.pbuf.preamble.alias  # type: ignore[attr-defined]

    @property
    def brief(self) -> str:
        "Brief description of entity."
        return self.pbuf.preamble.doc.brief  # type: ignore[attr-defined]

    @property
    def description(self) -> str:
        "More verbose description of entity."
        return self.pbuf.preamble.doc.description  # type: ignore[attr-defined]


class _P4NamedMixin(_P4Bridged[_T]):
    """Generic base class for entities with an ID and name (not at top level)."""

    @property
    def id(self) -> int:
        "Entity ID."
        return self.pbuf.id  # type: ignore[attr-defined]

    @property
    def name(self) -> str:
        "Entity name."
        return self.pbuf.name  # type: ignore[attr-defined]


class P4EntityMap(Generic[_T]):
    "Maps names and ID's to entities."

    _by_name: dict[str, _T]
    _by_id: dict[int, _T]
    _entry_type: str

    def __init__(self, entry_type: str) -> None:
        self._by_name = {}
        self._by_id = {}
        self._entry_type = entry_type

    def get(self, key: str | int) -> _T | None:
        "Retrieve item by name of ID."
        if isinstance(key, int):
            return self._by_id.get(key)
        return self._by_name.get(key)

    def __getitem__(self, key: str | int) -> _T:
        "Retrieve item by name or ID."
        try:
            if isinstance(key, int):
                return self._by_id[key]
            return self._by_name[key]
        except KeyError:
            self._key_error(key)

    def __iter__(self) -> Iterator[_T]:
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    def __repr__(self) -> str:
        return f"[{', '.join([repr(item) for item in self])}]"

    def _add(self, entity: _T, split_suffix: bool = False) -> None:
        name = entity.name  # type: ignore[attr-defined]
        assert name not in self._by_name

        self._by_id[entity.id] = entity  # type: ignore[attr-defined]
        self._by_name[name] = entity

        if hasattr(entity, "alias"):
            alias = entity.alias  # type: ignore[attr-defined]
            if name != alias:
                assert alias not in self._by_name
                self._by_name[alias] = entity
            elif split_suffix and "." in alias:
                _, suffix = alias.rsplit(".", 2)
                assert suffix not in self._by_name, f"{suffix} exists!"
                self._by_name[suffix] = entity

    def _key_error(self, key: str | int):
        if isinstance(key, int):
            raise ValueError(f"no {self._entry_type} with id={key!r}") from None

        def _lev(s):
            return pylev.wfi_levenshtein(s, key)

        if not self._by_name:
            # No key's present at all? (e.g. action has no parameters)
            raise ValueError(
                f"no {self._entry_type}s present; you asked for {key!r}?"
            ) from None

        suggest = [s for s in self._by_name.keys() if s.endswith(f".{key}")]
        if not suggest:
            suggest = [min(self._by_name.keys(), key=_lev)]
        if len(suggest) == 1:
            suggest = suggest[0]

        raise ValueError(
            f"no {self._entry_type} named {key!r}. Did you mean {suggest!r}?"
        ) from None


# ~~~~~~~~~~~~~~~
# P 4 S c h e m a
# ~~~~~~~~~~~~~~~


class _P4Defs:
    "Sharable copy of de-normalized P4Info elements."

    tables: P4EntityMap["P4Table"]
    actions: P4EntityMap["P4Action"]
    action_profiles: P4EntityMap["P4ActionProfile"]
    controller_packet_metadata: P4EntityMap["P4ControllerPacketMetadata"]
    direct_counters: P4EntityMap["P4DirectCounter"]
    direct_meters: P4EntityMap["P4DirectMeter"]
    counters: P4EntityMap["P4Counter"]
    meters: P4EntityMap["P4Meter"]
    registers: P4EntityMap["P4Register"]
    digests: P4EntityMap["P4Digest"]
    type_info: "P4TypeInfo"

    def __init__(self, p4info: p4i.P4Info):
        "Initialize P4Info elements."

        self.tables = P4EntityMap("P4Table")
        self.actions = P4EntityMap("P4Action")
        self.action_profiles = P4EntityMap("P4ActionProfile")
        self.controller_packet_metadata = P4EntityMap("P4ControllerPacketMetadata")
        self.direct_counters = P4EntityMap("P4DirectCounter")
        self.direct_meters = P4EntityMap("P4DirectMeter")
        self.counters = P4EntityMap("P4Counter")
        self.meters = P4EntityMap("P4Meter")
        self.registers = P4EntityMap("P4Register")
        self.digests = P4EntityMap("P4Digest")
        self.type_info = P4TypeInfo(p4info.type_info)

        for entity in p4info.actions:
            self.actions._add(P4Action(entity))

        for entity in p4info.action_profiles:
            self.action_profiles._add(P4ActionProfile(entity))

        for entity in p4info.controller_packet_metadata:
            self.controller_packet_metadata._add(P4ControllerPacketMetadata(entity))

        for entity in p4info.direct_counters:
            self.direct_counters._add(P4DirectCounter(entity))

        for entity in p4info.direct_meters:
            self.direct_meters._add(P4DirectMeter(entity))

        for entity in p4info.counters:
            self.counters._add(P4Counter(entity))

        for entity in p4info.meters:
            self.meters._add(P4Meter(entity))

        for entity in p4info.registers:
            self.registers._add(P4Register(entity))

        for entity in p4info.digests:
            self.digests._add(P4Digest(entity))

        for entity in p4info.tables:
            self.tables._add(P4Table(entity, self))

        for action_profile in self.action_profiles:
            action_profile._finish_init(self)

        for register in self.registers:
            register._finish_init(self)

        for digest in self.digests:
            digest._finish_init(self)


def _load_p4info(data: p4i.P4Info | Path | None) -> tuple[p4i.P4Info | None, _P4Defs]:
    "Load P4Info from cache if possible."

    if data is None:
        return None, _EMPTY_P4DEFS

    if isinstance(data, Path):
        p4info = pbuf.from_text(data.read_text(), p4i.P4Info)
    else:
        assert isinstance(data, p4i.P4Info)
        p4info = data

    return p4info, _P4Defs(p4info)


class P4Schema(_ReprMixin):
    """Concrete class for accessing a P4Info file and API version info.

    TODO: This class stores information that may be shared across multiple
    switches with the exact same P4Info file. The current implementation does
    not share anything, and this is inefficient.
    """

    _p4info: p4i.P4Info | None
    _p4blob: Path | SupportsBytes | None
    _p4defs: _P4Defs
    _p4cookie: int = 0

    def __init__(
        self,
        p4info: p4i.P4Info | Path | None = None,
        p4blob: Path | SupportsBytes | None = None,
    ):
        "Parse P4Info information."

        self._p4info, self._p4defs = _load_p4info(p4info)
        self._p4blob = p4blob
        if self._p4info is not None:
            self._update_cookie()

    @property
    def is_configured(self) -> bool:
        "True if there's a p4info configured."
        return self._p4info is not None

    @property
    def p4info(self) -> p4i.P4Info:
        "P4Info value."
        assert self._p4info is not None
        return self._p4info

    def set_p4info(self, p4info: p4i.P4Info):
        "Set P4Info using value returned from switch."
        self._p4info, self._p4defs = _load_p4info(p4info)
        self._update_cookie()

    @property
    def p4blob(self) -> bytes:
        "a.k.a p4_device_config"
        if not self._p4blob:
            return b""
        if isinstance(self._p4blob, Path):
            return self._p4blob.read_bytes()
        return bytes(self._p4blob)

    @property
    def p4cookie(self) -> int:
        """Cookie value for p4info and p4blob."""
        return self._p4cookie

    def get_pipeline_config(self) -> p4r.ForwardingPipelineConfig:
        """The forwarding pipeline configuration."""

        return p4r.ForwardingPipelineConfig(
            p4info=self.p4info,
            p4_device_config=self.p4blob,
            cookie=p4r.ForwardingPipelineConfig.Cookie(cookie=self.p4cookie),
        )

    @property
    def name(self) -> str:
        "Name from pkg_info."
        assert self._p4info

        return self._p4info.pkg_info.name

    @property
    def version(self) -> str:
        "Version from pkg_info."
        assert self._p4info

        return self._p4info.pkg_info.version

    @property
    def arch(self) -> str:
        "Arch from pkg_info."
        assert self._p4info

        return self._p4info.pkg_info.arch

    @property
    def tables(self) -> P4EntityMap["P4Table"]:
        "Collection of P4 tables."
        return self._p4defs.tables

    @property
    def actions(self) -> P4EntityMap["P4Action"]:
        "Collection of P4 actions."
        return self._p4defs.actions

    @property
    def action_profiles(self) -> P4EntityMap["P4ActionProfile"]:
        "Collection of P4 action profiles."
        return self._p4defs.action_profiles

    @property
    def controller_packet_metadata(self) -> P4EntityMap["P4ControllerPacketMetadata"]:
        "Collection of P4 controller packet metadata."
        return self._p4defs.controller_packet_metadata

    @property
    def direct_counters(self) -> P4EntityMap["P4DirectCounter"]:
        "Collection of P4 direct counters."
        return self._p4defs.direct_counters

    @property
    def direct_meters(self) -> P4EntityMap["P4DirectMeter"]:
        "Collection of P4 direct meters."
        return self._p4defs.direct_meters

    @property
    def counters(self) -> P4EntityMap["P4Counter"]:
        "Collection of P4 counters."
        return self._p4defs.counters

    @property
    def meters(self) -> P4EntityMap["P4Meter"]:
        "Collection of P4 meters."
        return self._p4defs.meters

    @property
    def registers(self) -> P4EntityMap["P4Register"]:
        "Collection of P4 registers."
        return self._p4defs.registers

    @property
    def digests(self) -> P4EntityMap["P4Digest"]:
        "Collection of P4 digests."
        return self._p4defs.digests

    @property
    def type_info(self) -> "P4TypeInfo":
        "Type Info object."
        return self._p4defs.type_info

    def __str__(self):
        if self._p4info is None:
            return "<No P4Info>"
        return str(P4SchemaDescription(self))

    def _update_cookie(self):
        hasher = hashlib.sha256()
        hasher.update(self.p4info.SerializeToString(deterministic=True))
        hasher.update(self.p4blob)
        digest = hasher.digest()
        self._p4cookie = int.from_bytes(digest[0:8], "big")


def _sort_map(value):
    "Sort items in protobuf map in alphabetic order."

    result = list(value.items())
    result.sort()
    return result


class P4TypeInfo(_P4Bridged[p4t.P4TypeInfo]):
    "Represents a P4TypeInfo object."

    _headers: dict[str, "P4HeaderType"]
    _structs: dict[str, "P4StructType"]
    _header_unions: dict[str, "P4HeaderUnionType"]

    def __init__(self, pbuf: p4t.P4TypeInfo):
        super().__init__(pbuf)
        # The protobuf Mapping<K, V> types iterate over items in a
        # non-deterministic order. Sorts the keys in alphabetic
        # order to make comparison tests easier.
        self._headers = {
            name: P4HeaderType(item) for name, item in _sort_map(pbuf.headers)
        }
        self._structs = {
            name: P4StructType(item) for name, item in _sort_map(pbuf.structs)
        }
        self._header_unions = {
            name: P4HeaderUnionType(item)
            for name, item in _sort_map(pbuf.header_unions)
        }

        for value in self.structs.values():
            value._finish_init(self)

        for value in self.header_unions.values():
            value._finish_init(self)

    @property
    def headers(self):
        return self._headers

    @property
    def structs(self):
        return self._structs

    @property
    def header_unions(self):
        return self._header_unions


class P4SourceLocation(NamedTuple):
    "Represents location of code in a given source file."

    file: str
    "Path to the source file."

    line: int
    "Text line number in the source file, 1-based."

    column: int
    "Text column number in the line, 1-based."


class P4Annotation(NamedTuple):
    "Represents a P4 annotation (structured or unstructured)."

    name: str
    "Name of the annotation."

    body: str | tuple[Any, ...] | dict[str, Any]
    "Body of the annotation."

    location: P4SourceLocation | None
    "Location of the annotation."


def _parse_annotations(pbuf) -> list[P4Annotation]:
    """Return list of annotations in the protobuf message."""

    # If pbuf doesn't have an "annotations" property, try pbuf's "preamble".
    if not hasattr(pbuf, "annotations"):
        pbuf = pbuf.preamble

    result = []

    # Scan unstructured annotations.
    for i, annotation in enumerate(pbuf.annotations):
        loc = pbuf.annotation_locations[i] if pbuf.annotation_locations else None
        name, body = _parse_unstructured_annotation(annotation)
        result.append(P4Annotation(name, body, loc))

    # TODO: parse structured annotations...
    return result


_UNSTRUCTURED_ANNOTATION_REGEX = re.compile(r"@(\w+)(?:\((.*)\))?")


def _parse_unstructured_annotation(annotation: str) -> tuple[str, str]:
    m = _UNSTRUCTURED_ANNOTATION_REGEX.fullmatch(annotation)
    if not m:
        raise ValueError(f"Unsupported annotation: {annotation!r}")
    return (m[1], m[2])


class P4Table(_P4TopLevel[p4i.Table]):
    "Represents P4Table in schema."

    def __init__(self, pbuf: p4i.Table, defs: _P4Defs):
        super().__init__(pbuf)
        self._match_fields = P4EntityMap[P4MatchField]("match field")
        self._actions = P4EntityMap[P4ActionRef]("table action")

        for field in self.pbuf.match_fields:
            self._match_fields._add(P4MatchField(field))

        for ref in self.pbuf.action_refs:
            self._actions._add(P4ActionRef(ref, defs), split_suffix=True)

        # Resolve optional const_default_action_id.
        def_action_id = pbuf.const_default_action_id
        if def_action_id != 0:
            assert _check_id(def_action_id, "action")
            self._const_default_action = self._actions[def_action_id]
        else:
            self._const_default_action = None

        # Resolve optional implementation_id.
        impl_id = pbuf.implementation_id
        if impl_id != 0:
            assert _check_id(impl_id, "action_profile")
            self._action_profile = defs.action_profiles[impl_id]
        else:
            self._action_profile = None

        self._direct_counter = None
        self._direct_meter = None

        direct_resources = pbuf.direct_resource_ids
        assert len(direct_resources) <= 2
        for resource_id in direct_resources:
            if _check_id(resource_id, "direct_counter"):
                self._direct_counter = defs.direct_counters[resource_id]
            elif _check_id(resource_id, "direct_meter"):
                self._direct_meter = defs.direct_meters[resource_id]
            else:
                assert False, "Unexpected resource id"

    @property
    def size(self) -> int:
        return self.pbuf.size

    @property
    def match_fields(self):
        return self._match_fields

    @property
    def actions(self):
        return self._actions

    @property
    def const_default_action(self):
        return self._const_default_action

    @property
    def is_const(self):
        "True if table has static entries that cannot be modified at runtime."
        return self.pbuf.is_const_table

    @property
    def action_profile(self):
        return self._action_profile

    @property
    def idle_timeout_behavior(self):
        return P4IdleTimeoutBehavior(self.pbuf.idle_timeout_behavior)

    @property
    def direct_counter(self):
        return self._direct_counter

    @property
    def direct_meter(self):
        return self._direct_meter

    def encode_match(self, match):
        "Convert `match` to protobuf."
        result = []
        for key, value in match.items():
            try:
                result.append(self.match_fields[key].encode(value))
            except Exception as ex:
                raise ValueError(f"{self.name!r}: Match field {key!r}: {ex}") from ex
        return result

    def decode_match(self, match: list[p4r.FieldMatch]):
        "Convert protobuf `match` to a python dict."
        result = {}
        for field in match:
            fld = self.match_fields[field.field_id]
            result[fld.alias] = fld.decode(field)
        return result

    def encode_action(self, action):
        "Convert `action` to protobuf."
        try:
            act = self.actions[action["$action"]]
        except Exception as ex:
            raise ValueError(f"{self.name!r}: {ex}") from ex

        params = []
        for name, value in action.items():
            if name.startswith("$"):  # TODO: deal with $weight
                continue
            try:
                param = act.params[name]
                params.append(param.encode_param(value))
            except ValueError as ex:
                raise ValueError(f"{self.name!r}: {act.name!r}: {ex}") from ex
        return p4r.TableAction(action=p4r.Action(action_id=act.id, params=params))

    def decode_action(self, tbl_action: p4r.TableAction):
        "Convert protobuf `action` to python dict."
        match tbl_action.WhichOneof("type"):
            case "action":
                return self._decode_action(tbl_action.action)
            case "action_profile_member_id":
                member_id = tbl_action.action_profile_member_id
                return {"$member_id": member_id}
            case "action_profile_group_id":
                group_id = tbl_action.action_profile_group_id
                return {"$group_id": group_id}
            case "action_profile_action_set":
                action_set = tbl_action.action_profile_action_set
                return self._decode_action_set(action_set)

    def _decode_action(self, action: p4r.Action):
        act = self.actions[action.action_id]
        result = {"$action": act.alias}
        for param in action.params:
            act_param = act.params[param.param_id]
            value = act_param.decode_param(param)
            result[act_param.name] = value
        return result

    def _decode_action_set(self, action_set: p4r.ActionProfileActionSet):
        result = []
        for action in action_set.action_profile_actions:
            actval = self._decode_action(action.action)
            actval["$weight"] = (action.weight, action.watch_port)
            result.append(actval)
        return result


class P4ActionParam(_P4AnnoMixin, _P4DocMixin, _P4NamedMixin[p4i.Action.Param]):
    @property
    def bitwidth(self):
        return self.pbuf.bitwidth

    # TODO: type_name property

    def encode_param(self, value) -> p4r.Action.Param:
        "Encode `param` to protobuf."
        return p4r.Action.Param(
            param_id=self.id,
            value=values.encode_exact(value, self.bitwidth),
        )

    def decode_param(self, param: p4r.Action.Param):
        "Decode protobuf `param`."
        return values.decode_exact(param.value, self.bitwidth)


class P4Action(_P4TopLevel[p4i.Action]):
    def __init__(self, pbuf) -> None:
        super().__init__(pbuf)
        self._params = P4EntityMap[P4ActionParam]("action parameter")
        for param in self.pbuf.params:
            self._params._add(P4ActionParam(param))

    @property
    def params(self):
        return self._params


class P4ActionRef(_P4AnnoMixin, _P4Bridged[p4i.ActionRef]):
    def __init__(self, pbuf: p4i.ActionRef, defs: _P4Defs) -> None:
        super().__init__(pbuf)
        self._action = defs.actions[pbuf.id]

    @property
    def id(self):
        return self._action.id

    @property
    def name(self):
        return self._action.name

    @property
    def alias(self):
        return self._action.alias

    @property
    def params(self):
        return self._action._params

    @property
    def scope(self):
        return P4ActionScope(self.pbuf.scope)


class P4ActionProfile(_P4TopLevel[p4i.ActionProfile]):

    _actions: P4EntityMap[P4Action]

    def __init__(self, pbuf: p4i.ActionProfile):
        super().__init__(pbuf)
        self._actions = P4EntityMap("action")

    def _finish_init(self, defs: _P4Defs):
        table = defs.tables[self.pbuf.table_ids[0]]
        for action in table.actions:
            self._actions._add(defs.actions[action.id])

    @property
    def with_selector(self) -> bool:
        return self.pbuf.with_selector

    @property
    def size(self) -> int:
        return self.pbuf.size

    @property
    def max_group_size(self) -> int:
        return self.pbuf.max_group_size

    @property
    def actions(self) -> P4EntityMap[P4Action]:
        return self._actions


class P4MatchField(_P4DocMixin, _P4AnnoMixin, _P4NamedMixin[p4i.MatchField]):
    "Represents the P4Info MatchField protobuf."

    def __init__(self, pbuf: p4i.MatchField) -> None:
        super().__init__(pbuf)
        self._alias = _make_alias(self.name)

    @property
    def alias(self) -> str:
        return self._alias

    @property
    def bitwidth(self) -> int:
        return self.pbuf.bitwidth

    @property
    def match_type(self) -> P4MatchType | str:
        which_one = self.pbuf.WhichOneof("match")
        if which_one == "match_type":
            return P4MatchType(self.pbuf.match_type)
        assert which_one == "other_match_type"
        return self.pbuf.other_match_type

    def encode(self, value) -> p4r.FieldMatch:
        "Encode value as protobuf type."
        match self.match_type:
            case P4MatchType.EXACT:
                data = values.encode_exact(value, self.bitwidth)
                return p4r.FieldMatch(
                    field_id=self.id,
                    exact=p4r.FieldMatch.Exact(value=data),
                )
            case P4MatchType.LPM:
                data, prefix = values.encode_lpm(value, self.bitwidth)
                return p4r.FieldMatch(
                    field_id=self.id,
                    lpm=p4r.FieldMatch.LPM(value=data, prefix_len=prefix),
                )
            case P4MatchType.TERNARY:
                data, mask = values.encode_ternary(value, self.bitwidth)
                return p4r.FieldMatch(
                    field_id=self.id,
                    ternary=p4r.FieldMatch.Ternary(value=data, mask=mask),
                )
            case P4MatchType.OPTIONAL:
                data = values.encode_optional(value, self.bitwidth)
                return p4r.FieldMatch(
                    field_id=self.id,
                    optional=p4r.FieldMatch.Optional(value=data),
                )
            case other:
                raise ValueError(f"Unsupported match_type: {other!r}")

    def decode(self, field: p4r.FieldMatch):
        "Decode protobuf FieldMatch value."
        # TODO: check field type against self.match_type? Check id?
        match field.WhichOneof("field_match_type"):
            case "exact":
                return values.decode_exact(field.exact.value, self.bitwidth)
            case "lpm":
                return values.decode_lpm(
                    field.lpm.value, field.lpm.prefix_len, self.bitwidth
                )
            case other:
                raise ValueError(f"Unsupported match_type: {other!r}")


class P4ControllerPacketMetadata(_P4TopLevel[p4i.ControllerPacketMetadata]):
    def __init__(self, pbuf: p4i.ControllerPacketMetadata):
        super().__init__(pbuf)
        self._metadata = P4EntityMap[P4CPMetadata]("controller packet metadata")
        for metadata in pbuf.metadata:
            self._metadata._add(P4CPMetadata(metadata))

    @property
    def metadata(self):
        return self._metadata

    def encode_metadata(self, metadata: dict) -> list[p4r.PacketMetadata]:
        result = []
        for md in self.metadata:
            result.append(md.encode(metadata[md.name]))
        # for key, value in metadata.items():
        #    result.append(self.metadata[key].encode(value))
        return result

    def decode_metadata(self, metadata: list[p4r.PacketMetadata]) -> dict:
        "Convert protobuf `metadata` to a python dict."
        result = {}
        for field in metadata:
            data = self.metadata[field.metadata_id]
            result[data.name] = data.decode(field)
        return result


class P4CPMetadata(_P4AnnoMixin, _P4NamedMixin[p4i.ControllerPacketMetadata.Metadata]):
    @property
    def bitwidth(self):
        return self.pbuf.bitwidth

    def encode(self, value) -> p4r.PacketMetadata:
        data = values.encode_exact(value, self.bitwidth)
        return p4r.PacketMetadata(metadata_id=self.id, value=data)

    def decode(self, data: p4r.PacketMetadata):
        return values.decode_exact(data.value, self.bitwidth)


class P4DirectCounter(_P4TopLevel[p4i.DirectCounter]):
    @property
    def unit(self):
        return P4CounterUnit(self.pbuf.spec.unit)


class P4DirectMeter(_P4TopLevel[p4i.DirectMeter]):
    @property
    def unit(self):
        return P4MeterUnit(self.pbuf.spec.unit)


class P4Counter(_P4TopLevel[p4i.Counter]):
    @property
    def size(self) -> int:
        return self.pbuf.size

    @property
    def unit(self) -> P4CounterUnit:
        return P4CounterUnit(self.pbuf.spec.unit)


class P4Meter(_P4TopLevel[p4i.Meter]):
    @property
    def size(self) -> int:
        return self.pbuf.size

    @property
    def unit(self) -> P4MeterUnit:
        return P4MeterUnit(self.pbuf.spec.unit)


class P4BitsType(_P4AnnoMixin, _P4Bridged[p4t.P4BitstringLikeTypeSpec]):
    "Represents the P4 Bitstring type."

    _bitwidth: int
    _signed: bool = False
    _varbit: bool = False

    def __init__(self, pbuf: p4t.P4BitstringLikeTypeSpec):
        super().__init__(pbuf)
        match pbuf.WhichOneof("type_spec"):
            case "bit":
                self._bitwidth = pbuf.bit.bitwidth
            case "int":
                self._bitwidth = pbuf.int.bitwidth
                self._signed = True
            case "varbit":
                self._bitwidth = pbuf.varbit.max_bitwidth
                self._varbit = True
            case other:
                raise ValueError(f"unknown oneof: {other!r}")

    @property
    def bitwidth(self) -> int:
        return self._bitwidth

    @property
    def signed(self) -> bool:
        return self._signed

    @property
    def varbit(self) -> bool:
        return self._varbit

    def encode_bytes(self, value: Any) -> bytes:
        # TODO: Implement signed and varbit.
        assert not self.signed and not self.varbit
        return values.encode_exact(value, self.bitwidth)

    def decode_bytes(self, data: bytes) -> Any:
        # TODO: Implement signed and varbit.
        assert not self.signed and not self.varbit
        return values.decode_exact(data, self.bitwidth)

    def encode_data(self, value: Any) -> p4d.P4Data:
        return p4d.P4Data(bitstring=self.encode_bytes(value))

    def decode_data(self, data: p4d.P4Data) -> Any:
        return self.decode_bytes(data.bitstring)


class P4BoolType(_P4Bridged[p4t.P4BoolType]):
    "Represents the P4 Bool type (which is empty)."

    def encode_data(self, value: bool) -> p4d.P4Data:
        return p4d.P4Data(bool=value)

    def decode_data(self, data: p4d.P4Data) -> bool:
        return data.bool


class P4HeaderType(_P4AnnoMixin, _P4Bridged[p4t.P4HeaderTypeSpec]):
    "Represents P4HeaderTypeSpec."

    _members: dict[str, P4BitsType]  # insertion order matters

    def __init__(self, pbuf: p4t.P4HeaderTypeSpec):
        super().__init__(pbuf)
        self._members = {item.name: P4BitsType(item.type_spec) for item in pbuf.members}

    @property
    def members(self) -> dict[str, P4BitsType]:
        return self._members

    def encode_data(self, value: dict) -> p4d.P4Data:
        # TODO: Handle valid but memberless header?
        if not value:
            return p4d.P4Data(header=p4d.P4Header(is_valid=False))

        bitstrings = [typ.encode_bytes(value[key]) for key, typ in self.members.items()]
        return p4d.P4Data(header=p4d.P4Header(is_valid=True, bitstrings=bitstrings))

    def decode_data(self, data: p4d.P4Data) -> dict:
        # TODO: Handle valid but memberless header?
        header = data.header

        if not header.is_valid:
            if header.bitstrings:
                raise ValueError(f"invalid header with bitstrings: {header!r}")
            return {}

        if len(header.bitstrings) != len(self.members):
            raise ValueError(f"invalid header size: {header!r}")

        result = {}
        i = 0
        for key, typ in self.members.items():
            result[key] = typ.decode_bytes(header.bitstrings[i])
            i += 1

        return result


class P4HeaderUnionType(_P4AnnoMixin, _P4Bridged[p4t.P4HeaderUnionTypeSpec]):
    _members: dict[str, P4HeaderType]

    def __init__(self, pbuf: p4t.P4HeaderUnionTypeSpec):
        super().__init__(pbuf)
        self._members = {}

    def _finish_init(self, type_info: P4TypeInfo):
        self._members = {
            member.name: type_info.headers[member.header.name]
            for member in self.pbuf.members
        }

    @property
    def members(self) -> dict[str, P4HeaderType]:
        return self._members

    def encode_data(self, value: dict) -> p4d.P4Data:
        raise NotImplementedError("unimplemented")

    def decode_data(self, data: p4d.P4Data) -> dict:
        raise NotImplementedError("unimplemented")


class P4HeaderStackType(_P4AnnoMixin, _P4Bridged[p4t.P4HeaderStackTypeSpec]):
    _header: P4HeaderType

    def __init__(self, pbuf, type_info: P4TypeInfo):
        super().__init__(pbuf)
        self._header = type_info.headers[self.pbuf.header.name]

    @property
    def header(self) -> P4HeaderType:
        return self._header

    @property
    def size(self) -> int:
        return self.pbuf.size

    def encode_data(self, value: dict) -> p4d.P4Data:
        raise NotImplementedError("unimplemented")

    def decode_data(self, data: p4d.P4Data) -> dict:
        raise NotImplementedError("unimplemented")


class P4HeaderUnionStackType(_P4AnnoMixin, _P4Bridged[p4t.P4HeaderUnionStackTypeSpec]):
    _header_union: P4HeaderUnionType

    def __init__(self, pbuf, type_info: P4TypeInfo):
        super().__init__(pbuf)
        self._header_union = type_info.header_unions[self.pbuf.header_union.name]

    @property
    def header_union(self) -> P4HeaderUnionType:
        return self._header_union

    @property
    def size(self) -> int:
        return self.pbuf.size

    def encode_data(self, value: dict) -> p4d.P4Data:
        raise NotImplementedError("unimplemented")

    def decode_data(self, data: p4d.P4Data) -> dict:
        raise NotImplementedError("unimplemented")


class P4StructType(_P4AnnoMixin, _P4Bridged[p4t.P4StructTypeSpec]):
    "Represents P4StructTypeSpec."

    _members: dict[str, "_P4Type"]  # insertion order matters

    def __init__(self, pbuf: p4t.P4StructTypeSpec):
        super().__init__(pbuf)
        self._members = {}

    def _finish_init(self, type_info: P4TypeInfo):
        self._members = {
            item.name: _parse_type_spec(item.type_spec, type_info)
            for item in self.pbuf.members
        }

    @property
    def members(self) -> dict[str, "_P4Type"]:
        return self._members

    def encode_data(self, value: dict) -> p4d.P4Data:
        members = [typ.encode_data(value[key]) for key, typ in self.members.items()]
        return p4d.P4Data(struct=p4d.P4StructLike(members=members))

    def decode_data(self, data: p4d.P4Data) -> dict:
        struct = data.struct
        if len(struct.members) != len(self.members):
            raise ValueError(f"invalid struct size: {struct!r}")

        result = {}
        i = 0
        for key, typ in self.members.items():
            result[key] = typ.decode_data(struct.members[i])
            i += 1

        return result


class P4TupleType(_P4AnnoMixin, _P4Bridged[p4t.P4TupleTypeSpec]):
    "Represents P4TupleTypeSpec."

    _members: list["_P4Type"]

    def __init__(self, pbuf: p4t.P4TupleTypeSpec, type_info: P4TypeInfo):
        super().__init__(pbuf)
        self._members = [
            _parse_type_spec(item, type_info) for item in self.pbuf.members
        ]

    @property
    def members(self) -> list["_P4Type"]:
        return self._members

    def encode_data(self, value: dict) -> p4d.P4Data:
        raise NotImplementedError("unimplemented")

    def decode_data(self, data: p4d.P4Data) -> dict:
        raise NotImplementedError("unimplemented")


_P4Type = (
    P4BitsType
    | P4BoolType
    | P4TupleType
    | P4StructType
    | P4HeaderType
    | P4HeaderUnionType
    | P4HeaderStackType
    | P4HeaderUnionStackType
)


def _parse_type_spec(type_spec: p4t.P4DataTypeSpec, type_info: P4TypeInfo) -> _P4Type:
    match type_spec.WhichOneof("type_spec"):
        case "bitstring":
            return P4BitsType(type_spec.bitstring)
        case "bool":
            return P4BoolType(type_spec.bool)
        case "tuple":
            return P4TupleType(type_spec.tuple, type_info)
        case "struct":
            return type_info.structs[type_spec.struct.name]
        case "header":
            return type_info.headers[type_spec.header.name]
        case "header_union":
            return type_info.header_unions[type_spec.header_union.name]
        case "header_stack":
            return P4HeaderStackType(type_spec.header_stack, type_info)
        case "header_union_stack":
            return P4HeaderUnionStackType(type_spec.header_union_stack, type_info)
        # TODO: "enum", "error", "serializable_enum", "new_type"
        case other:
            raise ValueError(f"unknown type_spec: {other!r}")


class P4Register(_P4TopLevel[p4i.Register]):
    _type_spec: _P4Type | None = None

    def _finish_init(self, defs: _P4Defs):
        self._type_spec = _parse_type_spec(self.pbuf.type_spec, defs.type_info)

    # TODO: index_type_name

    @property
    def type_spec(self) -> _P4Type:
        assert self._type_spec is not None
        return self._type_spec

    @property
    def size(self) -> int:
        return self.pbuf.size


class P4Digest(_P4TopLevel[p4i.Digest]):
    _type_spec: _P4Type

    def _finish_init(self, defs: _P4Defs):
        self._type_spec = _parse_type_spec(self.pbuf.type_spec, defs.type_info)

    @property
    def type_spec(self) -> _P4Type:
        return self._type_spec


def _make_alias(name: str) -> str:
    return name.split(".")[-1]


def _check_id(id: int, entity_type: str) -> bool:
    "Return true if ID belongs to the specified entity type."
    id_prefix = getattr(p4i.P4Ids.Prefix, entity_type.upper())
    return (id >> 24) == id_prefix


class P4SchemaDescription:
    "Helper class to produce text description of a P4Schema."

    CLIPBOARD = "\U0001F4CB"  # Clipboard
    PACKAGE = "\U0001F4E6"  # Package
    LABEL = "\U0001F3F7"
    INBOX = "\U0001F4E5"
    OUTBOX = "\U0001F4E4"

    MATCH_TYPES = {
        P4MatchType.EXACT: "=",
        P4MatchType.LPM: "*",
        P4MatchType.TERNARY: "/",
        P4MatchType.RANGE: "…",
        P4MatchType.OPTIONAL: "?",
    }

    def __init__(self, schema: P4Schema):
        self._schema = schema

    def __str__(self) -> str:
        result = self._describe_preamble()
        for table in self._schema.tables:
            result += self._describe_table(table)
        for metadata in self._schema.controller_packet_metadata:
            result += self._describe_packet_metadata(metadata)
        return result

    def _describe_preamble(self) -> str:
        "Describe preamble."

        sch = self._schema
        return f"{sch.name} (version={sch.version}, arch={sch.arch})\n"

    def _describe_match_type(self, match_type: P4MatchType | str):
        "Return a string describing the match type."

        if isinstance(match_type, str):
            return f"[{match_type}]"
        else:
            return self.MATCH_TYPES[match_type]

    def _describe_table(self, table: P4Table) -> str:
        "Describe P4Table."

        # Table header
        line = f"{self.CLIPBOARD}{table.alias}[{table.size}]"
        if table.action_profile:
            line += f" -> {self._describe_ap(table.action_profile)}"
        line += "\n"

        # Table fields
        line += "  "
        for field in table.match_fields:
            match_type = self._describe_match_type(field.match_type)
            line += f"{field.alias}{match_type}{field.bitwidth} "
        line += "\n"

        # Table actions
        line += "  "
        for action in table.actions:
            line += self._describe_action(action)
        line += "\n"

        return line

    def _describe_ap(self, ap: P4ActionProfile) -> str:
        "Describe P4ActionProfile."
        opts = []
        if ap.with_selector:
            opts.append("selector")
            opts.append(f"max_group_size={ap.max_group_size}")

        return f"{self.PACKAGE}{ap.alias}[{ap.size}] { ', '.join(opts) }"

    def _describe_action(self, action: P4ActionRef):
        "Describe P4ActionRef."
        params = ", ".join(f"{p.name}:{p.bitwidth}" for p in action.params)
        return f"{action.alias}({params}) "

    def _describe_packet_metadata(self, metadata: P4ControllerPacketMetadata):
        "Describe P4ControllerPacketMetadata."
        symbol = self.INBOX
        if metadata.alias == "packet_out":
            symbol = self.OUTBOX

        total_bits = 0
        for md in metadata.metadata:
            total_bits += md.bitwidth
        line = f"{symbol}{metadata.alias} ({total_bits//8} bytes)\n  "
        for md in metadata.metadata:
            line += f"{md.name}:{md.bitwidth} "
        line += "\n"

        return line


_EMPTY_P4DEFS = _P4Defs(p4i.P4Info())
