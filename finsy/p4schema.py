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

# pyright: reportPrivateUsage=false

import hashlib
import inspect
import re
from pathlib import Path
from typing import (
    Any,
    Generic,
    Iterator,
    Mapping,
    NamedTuple,
    Sequence,
    SupportsBytes,
    TypeVar,
    cast,
)

import pylev

from finsy import p4values
from finsy import pbuf as pbuf_util
from finsy.grpcutil import GRPCStatusCode, _EnumBase
from finsy.log import LOGGER
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

    def vt(self) -> p4r.GetForwardingPipelineConfigRequest.ResponseType.ValueType:
        return cast(p4r.GetForwardingPipelineConfigRequest.ResponseType.ValueType, self)


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

    def vt(self) -> p4r.SetForwardingPipelineConfigRequest.Action.ValueType:
        return cast(p4r.SetForwardingPipelineConfigRequest.Action.ValueType, self)


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

    def vt(self) -> p4r.Update.Type.ValueType:
        return cast(p4r.Update.Type.ValueType, self)


def _validate_enum(enum_class: Any, pbuf_class: Any):
    "Verify that our enum class contains the same members as the protobuf."
    for name, value in pbuf_class.items():
        assert enum_class[name].value == value, name


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

_EXEMPT_PROPERTIES = {"pbuf", "p4info", "p4blob"}


class _ReprMixin:
    """Mixin class to implement a generic __repr__ method.

    Output only includes explicit object properties (using @property).
    Property values that are redundant or verbose are exempt.
    """

    def __repr__(self) -> str:
        cls = type(self)
        properties = [
            name
            for (name, _) in inspect.getmembers(cls, inspect.isdatadescriptor)
            if not name.startswith("_") and name not in _EXEMPT_PROPERTIES
        ]

        attrs = [f"{name}={getattr(self, name)!r}" for name in properties]
        return f"{cls.__name__}({', '.join(attrs)})"


_T = TypeVar("_T")


class _P4Bridged(_ReprMixin, Generic[_T]):
    """Generic base class that wraps a corresponding protobuf message <T>.

    You can access the protobuf using the `.pbuf` property.
    """

    pbuf: _T
    "Corresponding protobuf message."

    def __init__(self, pbuf: _T):
        self.pbuf = pbuf


class _P4AnnoMixin:
    """Mixin class for entities and sub-entities that have annotations.

    Overrides __init__. Must be placed first.
    """

    _annotations: list["P4Annotation"]

    def __init__(self, pbuf: Any):
        super().__init__(pbuf)  # pyright: ignore[reportGeneralTypeIssues]
        self._annotations = _parse_annotations(pbuf)

    @property
    def annotations(self) -> list["P4Annotation"]:
        "Annotations associated with the entity."
        return self._annotations


class _P4DocMixin:
    "Mixin class for sub-entities that have descriptions."

    @property
    def brief(self) -> str:
        return self.pbuf.doc.brief  # type: ignore[attr-defined]

    @property
    def description(self) -> str:
        return self.pbuf.doc.description  # type: ignore[attr-defined]


class _P4TopLevel(_P4AnnoMixin, _P4Bridged[_T]):
    """Generic base class for entities at the top level of the P4Info file."""

    _id: int  # cache for performance

    def __init__(self, pbuf: Any):
        super().__init__(pbuf)
        self._id = pbuf.preamble.id

    @property
    def id(self) -> int:
        "Entity ID."
        return self._id

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

    _id: int  # cache for performance

    def __init__(self, pbuf: Any):
        super().__init__(pbuf)
        self._id = pbuf.id

    @property
    def id(self) -> int:
        "Entity ID."
        return self._id

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
        value = self.get(key)
        if value is None:
            self._key_error(key)
        return value

    def __iter__(self) -> Iterator[_T]:
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    def __repr__(self) -> str:
        return f"[{', '.join([repr(item) for item in self])}]"

    def _add(self, entity: _T, split_suffix: bool = False) -> None:
        "Add entity."
        ident: int = entity.id  # type: ignore[attr-defined]
        name: str = entity.name  # type: ignore[attr-defined]

        if ident in self._by_id:
            raise ValueError(f"id already exists: {ident!r}")

        self._by_id[ident] = entity
        self._add_name(name, entity)

        if hasattr(entity, "alias"):
            alias: str = entity.alias  # type: ignore[attr-defined]
            if name != alias:
                self._add_name(alias, entity)
            elif split_suffix and "." in alias:
                _, suffix = alias.rsplit(".", 2)
                self._add_name(suffix, entity)

    def _add_name(self, name: str, entity: _T):
        "Add entity by name."
        if name in self._by_name:
            raise ValueError(r"name already exists: {name!r}")
        self._by_name[name] = entity

    def _key_error(self, key: str | int):
        if isinstance(key, int):
            raise ValueError(f"no {self._entry_type} with id={key!r}") from None

        def _lev(val: str) -> int:
            return pylev.wfi_levenshtein(val, key)

        if not self._by_name:
            # No key's present at all? (e.g. action has no parameters)
            raise ValueError(
                f"no {self._entry_type}s present; you asked for {key!r}?"
            ) from None

        suggest = [s for s in self._by_name if s.endswith(f".{key}")]
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
    value_sets: P4EntityMap["P4ValueSet"]
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
        self.value_sets = P4EntityMap("P4ValueSet")
        self.type_info = P4TypeInfo(p4info.type_info)

        for (name, cls) in [
            ("actions", P4Action),
            ("action_profiles", P4ActionProfile),
            ("controller_packet_metadata", P4ControllerPacketMetadata),
            ("direct_counters", P4DirectCounter),
            ("direct_meters", P4DirectMeter),
            ("counters", P4Counter),
            ("meters", P4Meter),
            ("registers", P4Register),
            ("digests", P4Digest),
            ("value_sets", P4ValueSet),
        ]:
            obj = getattr(self, name)
            for entity in getattr(p4info, name):
                obj._add(cls(entity))

        for entity in p4info.tables:
            self.tables._add(P4Table(entity, self))

        for iterable in (
            self.actions,
            self.action_profiles,
            self.controller_packet_metadata,
            self.registers,
            self.digests,
            self.direct_counters,
            self.value_sets,
        ):
            for obj in iterable:
                obj._finish_init(self)


def _load_p4info(data: p4i.P4Info | Path | None) -> tuple[p4i.P4Info | None, _P4Defs]:
    "Load P4Info from cache if possible."

    # FIXME: Actually implement a cache!?!

    if data is None:
        return None, _EMPTY_P4DEFS

    if isinstance(data, Path):
        p4info = pbuf_util.from_text(data.read_text(), p4i.P4Info)
    else:
        p4info = data

    assert isinstance(p4info, p4i.P4Info)
    return p4info, _P4Defs(p4info)


class P4Schema(_ReprMixin):
    """Concrete class for accessing a P4Info file and API version info.

    TODO: This class stores information that may be shared across multiple
    switches with the exact same P4Info file. The current implementation does
    not share anything, and this is inefficient.
    """

    _p4info: p4i.P4Info | None
    _p4blob: Path | bytes | SupportsBytes | None
    _p4defs: _P4Defs
    _p4cookie: int = 0

    def __init__(
        self,
        p4info: p4i.P4Info | Path | None = None,
        p4blob: Path | bytes | SupportsBytes | None = None,
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
        if self._p4info is None:
            raise ValueError("No P4Info configured.")
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

    def get_pipeline_info(self) -> str:
        "Concise string description of the pipeline (suitable for logging)."
        if self.is_configured:
            pipeline = self.name
            version = self.version
            arch = self.arch
            return f"{pipeline=} {version=} {arch=}"
        else:
            return "<No pipeline configured>"

    @property
    def name(self) -> str:
        "Name from pkg_info."
        if self._p4info is None:
            return ""
        return self._p4info.pkg_info.name

    @property
    def version(self) -> str:
        "Version from pkg_info."
        if self._p4info is None:
            return ""
        return self._p4info.pkg_info.version

    @property
    def arch(self) -> str:
        "Arch from pkg_info."
        if self._p4info is None:
            return ""
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
    def value_sets(self) -> P4EntityMap["P4ValueSet"]:
        "Collection of P4 value sets."
        return self._p4defs.value_sets

    @property
    def type_info(self) -> "P4TypeInfo":
        "Type Info object."
        return self._p4defs.type_info

    def __str__(self):
        if self._p4info is None:
            return "<P4Info: No pipeline configured>"
        return str(P4SchemaDescription(self))

    def _update_cookie(self):
        hasher = hashlib.sha256()
        hasher.update(self.p4info.SerializeToString(deterministic=True))
        hasher.update(self.p4blob)
        digest = hasher.digest()
        self._p4cookie = int.from_bytes(digest[0:8], "big")


def _sort_map(value: Mapping[Any, Any]):
    "Sort items in protobuf map in alphabetic order."

    return sorted(value.items())


class P4TypeInfo(_P4Bridged[p4t.P4TypeInfo]):
    "Represents a P4TypeInfo object."

    _headers: dict[str, "P4HeaderType"]
    _structs: dict[str, "P4StructType"]
    _header_unions: dict[str, "P4HeaderUnionType"]
    _new_types: dict[str, "P4NewType"]

    def __init__(self, pbuf: p4t.P4TypeInfo):
        super().__init__(pbuf)
        # The protobuf Mapping<K, V> types iterate over items in a
        # non-deterministic order. Sorts the keys in alphabetic
        # order to make comparison tests easier.
        self._headers = {
            name: P4HeaderType(name, item) for name, item in _sort_map(pbuf.headers)
        }
        self._structs = {
            name: P4StructType(name, item) for name, item in _sort_map(pbuf.structs)
        }
        self._header_unions = {
            name: P4HeaderUnionType(name, item)
            for name, item in _sort_map(pbuf.header_unions)
        }
        self._new_types = {
            name: P4NewType(name, item) for name, item in _sort_map(pbuf.new_types)
        }

        for item in (self._structs, self._header_unions, self._new_types):
            for value in item.values():
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

    @property
    def new_types(self):
        return self._new_types

    def __getitem__(self, name: str) -> "_P4Type":
        "Retrieve a named type used in a match-field or action-param."
        for search in (self._new_types, self._structs):
            result = search.get(name)
            if result is not None:
                return result
        raise KeyError(name)


class P4Annotation(NamedTuple):
    "Represents a P4 annotation (structured or unstructured)."

    name: str
    "Name of the annotation."

    body: str | tuple[Any, ...] | dict[str, Any]
    "Body of the annotation."


def _parse_annotations(pbuf: Any) -> list[P4Annotation]:
    """Return list of annotations in the protobuf message."""

    # If pbuf doesn't have an "annotations" property, try pbuf's "preamble".
    if not hasattr(pbuf, "annotations"):
        pbuf = pbuf.preamble

    result: list[P4Annotation] = []

    # Scan unstructured annotations.
    for annotation in pbuf.annotations:
        name, body = _parse_unstructured_annotation(annotation)
        result.append(P4Annotation(name, body))

    # TODO: parse structured annotations...
    return result


_UNSTRUCTURED_ANNOTATION_REGEX = re.compile(r"@(\w+)(?:\((.*)\))?", re.DOTALL)


def _parse_unstructured_annotation(annotation: str) -> tuple[str, str]:
    m = _UNSTRUCTURED_ANNOTATION_REGEX.fullmatch(annotation)
    if not m:
        raise ValueError(f"Unsupported annotation: {annotation!r}")
    return (m[1], m[2])


class P4Table(_P4TopLevel[p4i.Table]):
    "Represents Table in schema."

    _match_fields: P4EntityMap["P4MatchField"]
    _actions: P4EntityMap["P4ActionRef"]
    _const_default_action: "P4ActionRef | None"
    _action_profile: "P4ActionProfile | None"
    _direct_counter: "P4DirectCounter | None"
    _direct_meter: "P4DirectMeter | None"

    def __init__(self, pbuf: p4i.Table, defs: _P4Defs):
        super().__init__(pbuf)
        self._match_fields = P4EntityMap("match field")
        self._actions = P4EntityMap("table action")

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

        # Resolve match field type_specs.
        for field in self._match_fields:
            field._finish_init(defs)

        self._direct_counter = None
        self._direct_meter = None

        # Load direct resources.
        direct_resources = pbuf.direct_resource_ids
        assert len(direct_resources) <= 2

        for resource_id in direct_resources:
            if _check_id(resource_id, "direct_counter"):
                self._direct_counter = defs.direct_counters[resource_id]
            elif _check_id(resource_id, "direct_meter"):
                self._direct_meter = defs.direct_meters[resource_id]
            else:
                assert False, "Unexpected resource id"

        if self._direct_counter is not None:  # FIXME: move check into P4DirectCounter
            if self._direct_counter.direct_table_id != self.id:
                LOGGER.warning(
                    "P4Schema: Direct counter ID mismatch: %r",
                    self._direct_counter,
                )

        if self._direct_meter is not None:
            if self._direct_meter.direct_table_id != self.id:
                LOGGER.warning(
                    "P4Schema: Direct meter ID mismatch: %r",
                    self._direct_meter,
                )

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


class P4ActionParam(_P4AnnoMixin, _P4DocMixin, _P4NamedMixin[p4i.Action.Param]):
    "Represents 'Action.Param' in schema."

    _bitwidth: int  # cache for performance
    _type_spec: "_P4Type | None" = None

    def __init__(self, pbuf: p4i.Action.Param):
        super().__init__(pbuf)
        self._bitwidth = pbuf.bitwidth

    def _finish_init(self, defs: _P4Defs):
        if self.pbuf.HasField("type_name"):
            self._type_spec = defs.type_info[self.pbuf.type_name.name]

    @property
    def bitwidth(self) -> int:
        return self._bitwidth

    @property
    def type_spec(self) -> "_P4Type | None":
        return self._type_spec

    def encode_param(self, value: p4values.P4ParamValue) -> p4r.Action.Param:
        "Encode `param` to protobuf."
        return p4r.Action.Param(
            param_id=self.id,
            value=p4values.encode_exact(value, self._bitwidth),
        )

    def decode_param(self, param: p4r.Action.Param):
        "Decode protobuf `param`."
        return p4values.decode_exact(param.value, self._bitwidth)

    def format_param(self, value: p4values.P4ParamValue) -> str:
        "Format `param` as a string."
        format = p4values.DecodeFormat.STRING | p4values.DecodeFormat.ADDRESS
        return p4values.format_exact(value, self._bitwidth, format)


class P4Action(_P4TopLevel[p4i.Action]):
    "Represents Action in schema."

    _params: P4EntityMap[P4ActionParam]

    def __init__(self, pbuf: p4i.Action) -> None:
        super().__init__(pbuf)
        self._params = P4EntityMap[P4ActionParam]("action parameter")
        for param in self.pbuf.params:
            self._params._add(P4ActionParam(param))

    def _finish_init(self, defs: _P4Defs):
        for param in self._params:
            param._finish_init(defs)

    @property
    def params(self):
        return self._params


class P4ActionRef(_P4AnnoMixin, _P4Bridged[p4i.ActionRef]):
    "Represents ActionRef in schema."

    _id: int  # cache for performance
    _action: P4Action

    def __init__(self, pbuf: p4i.ActionRef, defs: _P4Defs) -> None:
        super().__init__(pbuf)
        self._action = defs.actions[pbuf.id]
        self._id = self._action.id

    @property
    def id(self):
        return self._id

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
    "Represents ActionProfile in schema."

    _actions: P4EntityMap[P4Action]
    _table_names: list[str]

    def __init__(self, pbuf: p4i.ActionProfile):
        super().__init__(pbuf)
        self._actions = P4EntityMap("action")

    def _finish_init(self, defs: _P4Defs):
        # Copy actions from first table.  FIXME: Is `actions` used anywhere?
        # Or, should this be the intersection of each table's actions?
        table = defs.tables[self.pbuf.table_ids[0]]
        for action in table.actions:
            self._actions._add(defs.actions[action.id])

        self._table_names = [
            defs.tables[table_id].alias for table_id in self.pbuf.table_ids
        ]
        self._table_names.sort()

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

    @property
    def table_names(self) -> list[str]:
        return self._table_names


class P4MatchField(_P4DocMixin, _P4AnnoMixin, _P4NamedMixin[p4i.MatchField]):
    "Represents the P4Info MatchField protobuf."

    _alias: str
    _bitwidth: int  # cache for performance
    _match_type: P4MatchType | str  # TODO: refactor into subclasses?
    _type_spec: "_P4Type | None" = None

    def __init__(self, pbuf: p4i.MatchField) -> None:
        super().__init__(pbuf)
        self._alias = _make_alias(self.name)
        self._bitwidth = pbuf.bitwidth

        match pbuf.WhichOneof("match"):
            case "match_type":
                self._match_type = P4MatchType(pbuf.match_type)
            case "other_match_type":
                self._match_type = pbuf.other_match_type
            case other:
                raise ValueError(f"unknown oneof: {other!r}")

    def _finish_init(self, defs: _P4Defs):
        if self.pbuf.HasField("type_name"):
            self._type_spec = defs.type_info[self.pbuf.type_name.name]

    @property
    def alias(self) -> str:
        return self._alias

    @property
    def bitwidth(self) -> int:
        return self._bitwidth

    @property
    def match_type(self) -> P4MatchType | str:
        return self._match_type

    @property
    def type_spec(self) -> "_P4Type | None":
        return self._type_spec

    def encode_field(self, value: Any) -> p4r.FieldMatch | None:
        "Encode value as protobuf type."

        match self.match_type:
            case P4MatchType.EXACT:
                data = p4values.encode_exact(value, self._bitwidth)
                return p4r.FieldMatch(
                    field_id=self.id,
                    exact=p4r.FieldMatch.Exact(value=data),
                )
            case P4MatchType.LPM:
                data, prefix = p4values.encode_lpm(value, self._bitwidth)
                if prefix == 0:  # "don't care" LPM match
                    return None
                return p4r.FieldMatch(
                    field_id=self.id,
                    lpm=p4r.FieldMatch.LPM(value=data, prefix_len=prefix),
                )
            case P4MatchType.TERNARY:
                data, mask = p4values.encode_ternary(value, self._bitwidth)
                if mask == b"\x00":  # "don't care" ternary match
                    return None
                return p4r.FieldMatch(
                    field_id=self.id,
                    ternary=p4r.FieldMatch.Ternary(value=data, mask=mask),
                )
            case P4MatchType.RANGE:
                low, high = p4values.encode_range(value, self._bitwidth)
                return p4r.FieldMatch(
                    field_id=self.id,
                    range=p4r.FieldMatch.Range(low=low, high=high),
                )
            case P4MatchType.OPTIONAL:
                if value is None:  # "don't care" optional match
                    return None
                data = p4values.encode_exact(value, self._bitwidth)
                return p4r.FieldMatch(
                    field_id=self.id,
                    optional=p4r.FieldMatch.Optional(value=data),
                )
            case other:
                raise ValueError(f"Unsupported match_type: {other!r}")

    def decode_field(self, field: p4r.FieldMatch):
        "Decode protobuf FieldMatch value."
        # TODO: check field type against self.match_type? Check id?
        match field.WhichOneof("field_match_type"):
            case "exact":
                return p4values.decode_exact(field.exact.value, self._bitwidth)
            case "lpm":
                return p4values.decode_lpm(
                    field.lpm.value, field.lpm.prefix_len, self._bitwidth
                )
            case "ternary":
                return p4values.decode_ternary(
                    field.ternary.value, field.ternary.mask, self._bitwidth
                )
            case "range":
                return p4values.decode_range(
                    field.range.low, field.range.high, self._bitwidth
                )
            case "optional":
                # Decode "optional" as exact value, if field is present.
                return p4values.decode_exact(field.optional.value, self._bitwidth)
            case other:
                raise ValueError(f"Unsupported match_type: {other!r}")

    def format_field(self, value: Any) -> str:
        "Format field value as string."

        format = p4values.DecodeFormat.STRING | p4values.DecodeFormat.ADDRESS
        match self.match_type:
            case P4MatchType.EXACT:
                return p4values.format_exact(value, self._bitwidth, format)
            case P4MatchType.LPM:
                return p4values.format_lpm(value, self._bitwidth, format)
            case P4MatchType.TERNARY:
                return p4values.format_ternary(value, self._bitwidth, format)
            case P4MatchType.RANGE:
                return p4values.format_range(value, self._bitwidth, format)
            case P4MatchType.OPTIONAL:
                return p4values.format_exact(value, self._bitwidth, format)
            case other:
                raise ValueError(f"Unsupported match_type: {other!r}")


class P4ControllerPacketMetadata(_P4TopLevel[p4i.ControllerPacketMetadata]):
    "Represents ControllerPacketMetadata in schema."

    _metadata: P4EntityMap["P4CPMetadata"]

    def __init__(self, pbuf: p4i.ControllerPacketMetadata):
        super().__init__(pbuf)
        self._metadata = P4EntityMap[P4CPMetadata]("controller packet metadata")
        for metadata in pbuf.metadata:
            self._metadata._add(P4CPMetadata(metadata))

    def _finish_init(self, defs: _P4Defs):
        for metadata in self._metadata:
            metadata._finish_init(defs)

    @property
    def metadata(self):
        return self._metadata

    def encode(self, metadata: dict[str, Any]) -> list[p4r.PacketMetadata]:
        "Encode python dict as protobuf `metadata`."
        result: list[p4r.PacketMetadata] = []

        for mdata in self.metadata:
            try:
                value = metadata[mdata.name]
            except KeyError:
                raise ValueError(
                    f"{self.name!r}: missing parameter {mdata.name!r}"
                ) from None
            result.append(mdata.encode(value))

        if len(metadata) > len(result):
            seen = set(metadata.keys()) - set(mdata.name for mdata in self.metadata)
            raise ValueError(f"{self.name!r}: extra parameters {seen!r}")

        return result

    def decode(self, metadata: Sequence[p4r.PacketMetadata]) -> dict[str, Any]:
        "Convert protobuf `metadata` to a python dict."
        result: dict[str, Any] = {}

        for field in metadata:
            data = self.metadata[field.metadata_id]
            result[data.name] = data.decode(field)

        return result


class P4CPMetadata(_P4AnnoMixin, _P4NamedMixin[p4i.ControllerPacketMetadata.Metadata]):
    "Represents ControllerPacketMetadata.Metadata in schema."

    _type_spec: "_P4Type | None" = None

    def _finish_init(self, defs: _P4Defs):
        if self.pbuf.HasField("type_name"):
            self._type_spec = defs.type_info[self.pbuf.type_name.name]

    @property
    def bitwidth(self) -> int:
        return self.pbuf.bitwidth

    @property
    def type_spec(self) -> "_P4Type | None":
        return self._type_spec

    def encode(self, value: p4values.P4ParamValue) -> p4r.PacketMetadata:
        data = p4values.encode_exact(value, self.bitwidth)
        return p4r.PacketMetadata(metadata_id=self.id, value=data)

    def decode(self, data: p4r.PacketMetadata):
        return p4values.decode_exact(data.value, self.bitwidth)


class P4DirectCounter(_P4TopLevel[p4i.DirectCounter]):
    "Represents DirectCounter in schema."

    _direct_table_name: str

    def _finish_init(self, defs: _P4Defs):
        direct_table = defs.tables[self.direct_table_id]
        assert direct_table.direct_counter == self
        self._direct_table_name = direct_table.name

    @property
    def unit(self):
        return P4CounterUnit(self.pbuf.spec.unit)

    @property
    def direct_table_id(self) -> int:
        return self.pbuf.direct_table_id

    @property
    def direct_table_name(self) -> str:
        return self._direct_table_name


class P4DirectMeter(_P4TopLevel[p4i.DirectMeter]):
    "Represents DirectMeter in schema."

    @property
    def unit(self):
        return P4MeterUnit(self.pbuf.spec.unit)

    @property
    def direct_table_id(self) -> int:
        return self.pbuf.direct_table_id


class P4Counter(_P4TopLevel[p4i.Counter]):
    "Represents Counter in schema."

    @property
    def size(self) -> int:
        return self.pbuf.size

    @property
    def unit(self) -> P4CounterUnit:
        return P4CounterUnit(self.pbuf.spec.unit)


class P4Meter(_P4TopLevel[p4i.Meter]):
    "Represents Meter in schema."

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
    def type_name(self) -> str:
        assert not self._varbit
        if not self._signed:
            return f"u{self.bitwidth}"
        return f"s{self.bitwidth}"

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
        return p4values.encode_exact(value, self.bitwidth)

    def decode_bytes(self, data: bytes) -> Any:
        # TODO: Implement signed and varbit.
        assert not self.signed and not self.varbit
        return p4values.decode_exact(data, self.bitwidth)

    def encode_data(self, value: Any) -> p4d.P4Data:
        return p4d.P4Data(bitstring=self.encode_bytes(value))

    def decode_data(self, data: p4d.P4Data) -> Any:
        return self.decode_bytes(data.bitstring)


class P4BoolType(_P4Bridged[p4t.P4BoolType]):
    "Represents the P4 Bool type (which is empty)."

    @property
    def type_name(self) -> str:
        return "bool"

    def encode_data(self, value: bool) -> p4d.P4Data:
        return p4d.P4Data(bool=value)

    def decode_data(self, data: p4d.P4Data) -> bool:
        return data.bool


class P4HeaderType(_P4AnnoMixin, _P4Bridged[p4t.P4HeaderTypeSpec]):
    "Represents P4HeaderTypeSpec."

    _type_name: str
    _members: dict[str, P4BitsType]  # insertion order matters

    def __init__(self, type_name: str, pbuf: p4t.P4HeaderTypeSpec):
        super().__init__(pbuf)
        self._type_name = type_name
        self._members = {item.name: P4BitsType(item.type_spec) for item in pbuf.members}

    @property
    def type_name(self) -> str:
        return self._type_name

    @property
    def members(self) -> dict[str, P4BitsType]:
        return self._members

    def encode_data(self, value: dict[str, Any]) -> p4d.P4Data:
        return p4d.P4Data(header=self.encode_header(value))

    def encode_header(self, value: dict[str, Any]) -> p4d.P4Header:
        # TODO: Handle valid but memberless header?
        if not value:
            return p4d.P4Header(is_valid=False)

        try:
            bitstrings = [
                typ.encode_bytes(value[key]) for key, typ in self.members.items()
            ]
        except KeyError as ex:
            raise ValueError(f"P4Header: missing field {ex.args[0]!r}") from None

        if len(value) > len(bitstrings):
            seen = set(value.keys()) - set(self.members.keys())
            raise ValueError(f"P4Header: extra parameters {seen!r}")

        return p4d.P4Header(is_valid=True, bitstrings=bitstrings)

    def decode_data(self, data: p4d.P4Data) -> dict[str, Any]:
        return self.decode_header(data.header)

    def decode_header(self, header: p4d.P4Header) -> dict[str, Any]:
        "Decode P4 header."

        # TODO: Handle valid but memberless header?
        if not header.is_valid:
            if header.bitstrings:
                raise ValueError(f"invalid header with bitstrings: {header!r}")
            return {}

        if len(header.bitstrings) != len(self.members):
            raise ValueError(f"invalid header size: {header!r}")

        result: dict[str, Any] = {}
        i = 0
        for key, typ in self.members.items():
            result[key] = typ.decode_bytes(header.bitstrings[i])
            i += 1

        return result


_HeaderUnionValue = dict[str, dict[str, Any]]


class P4HeaderUnionType(_P4AnnoMixin, _P4Bridged[p4t.P4HeaderUnionTypeSpec]):
    "Represents P4HeaderUnionTypeSpec."

    _type_name: str
    _members: dict[str, P4HeaderType]

    def __init__(self, type_name: str, pbuf: p4t.P4HeaderUnionTypeSpec):
        super().__init__(pbuf)
        self._type_name = type_name
        self._members = {}

    def _finish_init(self, type_info: P4TypeInfo):
        self._members = {
            member.name: type_info.headers[member.header.name]
            for member in self.pbuf.members
        }

    @property
    def type_name(self) -> str:
        return self._type_name

    @property
    def members(self) -> dict[str, P4HeaderType]:
        return self._members

    def encode_data(self, value: _HeaderUnionValue) -> p4d.P4Data:
        return p4d.P4Data(header_union=self.encode_union(value))

    def encode_union(self, value: _HeaderUnionValue) -> p4d.P4HeaderUnion:
        if len(value) > 1:
            raise ValueError(f"P4HeaderUnion: too many headers {value!r}")

        if not value:
            # No union members are valid.
            return p4d.P4HeaderUnion()

        header_name, header = next(iter(value.items()))

        try:
            header_type = self.members[header_name]
        except KeyError:
            raise ValueError(f"P4HeaderUnion: wrong header {header_name!r}") from None

        return p4d.P4HeaderUnion(
            valid_header_name=header_name,
            valid_header=header_type.encode_header(header),
        )

    def decode_data(self, data: p4d.P4Data) -> _HeaderUnionValue:
        return self.decode_union(data.header_union)

    def decode_union(self, header_union: p4d.P4HeaderUnion) -> _HeaderUnionValue:
        header_name = header_union.valid_header_name

        if not header_name:
            # No union members are valid.
            return {}

        header = self.members[header_name].decode_header(header_union.valid_header)
        return {header_name: header}


class P4HeaderStackType(_P4Bridged[p4t.P4HeaderStackTypeSpec]):
    "Represents P4HeaderStackTypeSpec."

    _header: P4HeaderType

    def __init__(self, pbuf: p4t.P4HeaderStackTypeSpec, type_info: P4TypeInfo):
        super().__init__(pbuf)
        self._header = type_info.headers[self.pbuf.header.name]

    @property
    def type_name(self) -> str:
        return f"{self.header.type_name}[{self.size}]"

    @property
    def header(self) -> P4HeaderType:
        return self._header

    @property
    def size(self) -> int:
        return self.pbuf.size

    def encode_data(self, value: Sequence[dict[str, Any]]) -> p4d.P4Data:
        if len(value) != self.size:
            raise ValueError(f"P4HeaderStack: expected {self.size} items")

        entries = [self.header.encode_header(val) for val in value]
        return p4d.P4Data(header_stack=p4d.P4HeaderStack(entries=entries))

    def decode_data(self, data: p4d.P4Data) -> Sequence[dict[str, Any]]:
        entries = data.header_stack.entries
        return [self.header.decode_header(header) for header in entries]


class P4HeaderUnionStackType(_P4Bridged[p4t.P4HeaderUnionStackTypeSpec]):
    "Represents P4HeaderUnionStackTypeSpec."

    _header_union: P4HeaderUnionType

    def __init__(self, pbuf: p4t.P4HeaderUnionStackTypeSpec, type_info: P4TypeInfo):
        super().__init__(pbuf)
        self._header_union = type_info.header_unions[self.pbuf.header_union.name]

    @property
    def type_name(self) -> str:
        return f"{self.header_union.type_name}[{self.size}]"

    @property
    def header_union(self) -> P4HeaderUnionType:
        return self._header_union

    @property
    def size(self) -> int:
        return self.pbuf.size

    def encode_data(self, value: Sequence[_HeaderUnionValue]) -> p4d.P4Data:
        if len(value) != self.size:
            raise ValueError(f"P4HeaderUnionStack: expected {self.size} items")

        entries = [self.header_union.encode_union(val) for val in value]
        return p4d.P4Data(header_union_stack=p4d.P4HeaderUnionStack(entries=entries))

    def decode_data(self, data: p4d.P4Data) -> list[_HeaderUnionValue]:
        entries = data.header_union_stack.entries
        return [self.header_union.decode_union(union) for union in entries]


class P4StructType(_P4AnnoMixin, _P4Bridged[p4t.P4StructTypeSpec]):
    "Represents P4StructTypeSpec."

    _type_name: str
    _members: dict[str, "_P4Type"]  # insertion order matters

    def __init__(self, type_name: str, pbuf: p4t.P4StructTypeSpec):
        super().__init__(pbuf)
        self._type_name = type_name
        self._members = {}

    def _finish_init(self, type_info: P4TypeInfo):
        self._members = {
            item.name: _parse_type_spec(item.type_spec, type_info)
            for item in self.pbuf.members
        }

    @property
    def type_name(self) -> str:
        return self._type_name

    @property
    def members(self) -> dict[str, "_P4Type"]:
        return self._members

    def encode_data(self, value: dict[str, Any]) -> p4d.P4Data:
        try:
            members = [typ.encode_data(value[key]) for key, typ in self.members.items()]
        except KeyError as ex:
            raise ValueError(f"P4Struct: missing field {ex.args[0]!r}") from None

        if len(value) > len(members):
            seen = set(value.keys()) - set(self.members.keys())
            raise ValueError(f"P4Struct: extra parameters {seen!r}")

        return p4d.P4Data(struct=p4d.P4StructLike(members=members))

    def decode_data(self, data: p4d.P4Data) -> dict[str, Any]:
        struct = data.struct
        if len(struct.members) != len(self.members):
            raise ValueError(f"invalid struct size: {struct!r}")

        result: dict[str, Any] = {}
        i = 0
        for key, typ in self.members.items():
            result[key] = typ.decode_data(struct.members[i])
            i += 1

        return result


class P4TupleType(_P4Bridged[p4t.P4TupleTypeSpec]):
    "Represents P4TupleTypeSpec."

    _members: list["_P4Type"]

    def __init__(self, pbuf: p4t.P4TupleTypeSpec, type_info: P4TypeInfo):
        super().__init__(pbuf)
        self._members = [
            _parse_type_spec(item, type_info) for item in self.pbuf.members
        ]

    @property
    def type_name(self) -> str:
        subtypes = ", ".join([subtype.type_name for subtype in self.members])
        return f"tuple[{subtypes}]"

    @property
    def members(self) -> list["_P4Type"]:
        return self._members

    def encode_data(self, value: tuple[Any, ...]) -> p4d.P4Data:
        if len(value) != len(self.members):
            raise ValueError(f"P4Tuple: expected {len(self.members)} items")

        members = [typ.encode_data(value[i]) for i, typ in enumerate(self.members)]
        return p4d.P4Data(tuple=p4d.P4StructLike(members=members))

    def decode_data(self, data: p4d.P4Data) -> tuple[Any, ...]:
        tuple_ = data.tuple
        if len(tuple_.members) != len(self.members):
            raise ValueError(f"invalid tuple size: {tuple_!r}")

        return tuple(
            typ.decode_data(val)
            for typ, val in zip(self.members, tuple_.members, strict=True)
        )


class P4NewTypeKind(_EnumBase):
    "Kind of P4NewType."

    ORIGINAL_TYPE = 1
    SDN_BITWIDTH = 2
    SDN_STRING = 3


class P4NewType(_P4Bridged[p4t.P4NewTypeSpec]):
    """Represents P4NewTypeSpec.

    A P4NewType is a type introduced with the `type` keyword in the P4 language.
    The new type can be represented by an original type or it can be translated
    at runtime from/to a uint (SDN_BITWIDTH) or string (SDN_STRING).

    This class uses the `.kind` accessor to indicate the kind of new type.
    The `original_*` and `translated_*` properties will raise an exception if
    the new type isn't the relevant kind.

    TODO: Possibly refactor this class into two classes: P4NewTypeOriginal and
    P4NewTypeTranslated.
    """

    _type_name: str
    _kind: P4NewTypeKind
    _original_type: "_P4Type | None" = None
    _translated_uri: str = ""
    _translated_bitwidth: int = 0

    def __init__(self, type_name: str, pbuf: p4t.P4NewTypeSpec):
        super().__init__(pbuf)
        self._type_name = type_name

        match self.pbuf.WhichOneof("representation"):
            case "original_type":
                self._kind = P4NewTypeKind.ORIGINAL_TYPE
            case "translated_type":
                translation = self.pbuf.translated_type
                match translation.WhichOneof("sdn_type"):
                    case "sdn_string":
                        self._kind = P4NewTypeKind.SDN_STRING
                    case "sdn_bitwidth":
                        self._kind = P4NewTypeKind.SDN_BITWIDTH
                        self._translated_bitwidth = translation.sdn_bitwidth
                    case other:
                        raise ValueError(f"unexpected oneof: {other!r}")
                self._translated_uri = translation.uri
            case other:
                raise ValueError(f"unexpected oneof: {other!r}")

    def _finish_init(self, type_info: P4TypeInfo):
        if self._kind == P4NewTypeKind.ORIGINAL_TYPE:
            self._original_type = _parse_type_spec(self.pbuf.original_type, type_info)

    @property
    def type_name(self) -> str:
        return self._type_name

    @property
    def kind(self) -> P4NewTypeKind:
        return self._kind

    @property
    def original_type(self) -> "_P4Type":
        assert self._kind == P4NewTypeKind.ORIGINAL_TYPE
        assert self._original_type is not None
        return self._original_type

    @property
    def translated_uri(self) -> str:
        assert self._kind != P4NewTypeKind.ORIGINAL_TYPE
        return self._translated_uri

    @property
    def translated_bitwidth(self) -> int:
        assert self._kind == P4NewTypeKind.SDN_BITWIDTH
        return self._translated_bitwidth

    def encode_bytes(self, value: Any) -> bytes:
        match self.kind:
            case P4NewTypeKind.SDN_BITWIDTH:
                return p4values.encode_exact(value, self.translated_bitwidth)
            case P4NewTypeKind.SDN_STRING:
                if isinstance(value, str):
                    value = value.encode()
                else:
                    assert isinstance(value, bytes)
                return value
            case P4NewTypeKind.ORIGINAL_TYPE:
                raise NotImplementedError()
            case other:
                raise ValueError(f"unexpected kind: {other!r}")

    def decode_bytes(self, data: bytes) -> Any:
        match self.kind:
            case P4NewTypeKind.SDN_BITWIDTH:
                return p4values.decode_exact(data, self.translated_bitwidth)
            case P4NewTypeKind.SDN_STRING:
                return data.decode()
            case P4NewTypeKind.ORIGINAL_TYPE:
                raise NotImplementedError()
            case other:
                raise ValueError(f"unexpected kind: {other!r}")

    def encode_data(self, value: Any) -> p4d.P4Data:
        match self.kind:
            case P4NewTypeKind.ORIGINAL_TYPE:
                return self.original_type.encode_data(value)
            case P4NewTypeKind.SDN_BITWIDTH | P4NewTypeKind.SDN_STRING:
                return p4d.P4Data(bitstring=self.encode_bytes(value))
            case other:
                raise ValueError(f"unexpected kind: {other!r}")

    def decode_data(self, data: p4d.P4Data) -> Any:
        match self.kind:
            case P4NewTypeKind.ORIGINAL_TYPE:
                return self.original_type.decode_data(data)
            case P4NewTypeKind.SDN_BITWIDTH | P4NewTypeKind.SDN_STRING:
                assert data.HasField("bitstring")
                return self.decode_bytes(data.bitstring)
            case other:
                raise ValueError(f"unexpected kind: {other!r}")

    def __repr__(self) -> str:
        match self.kind:
            case P4NewTypeKind.ORIGINAL_TYPE:
                result = f"P4NewType(original_type={self.original_type!r}"
            case P4NewTypeKind.SDN_STRING:
                result = f"P4NewType(sdn_string, uri={self.translated_uri!r}"
            case P4NewTypeKind.SDN_BITWIDTH:
                result = f"P4NewType(sdn_bitwidth={self.translated_bitwidth!r}, uri={self.translated_uri!r}"
            case other:
                raise ValueError(f"unexpected kind: {other!r}")
        return f"{result}, type_name={self.type_name!r})"


_P4Type = (
    P4BitsType
    | P4BoolType
    | P4TupleType
    | P4StructType
    | P4HeaderType
    | P4HeaderUnionType
    | P4HeaderStackType
    | P4HeaderUnionStackType
    | P4NewType
)


def _parse_type_spec(type_spec: p4t.P4DataTypeSpec, type_info: P4TypeInfo) -> _P4Type:
    match type_spec.WhichOneof("type_spec"):
        case "bitstring":
            result = P4BitsType(type_spec.bitstring)
        case "bool":
            result = P4BoolType(type_spec.bool)
        case "tuple":
            result = P4TupleType(type_spec.tuple, type_info)
        case "struct":
            result = type_info.structs[type_spec.struct.name]
        case "header":
            result = type_info.headers[type_spec.header.name]
        case "header_union":
            result = type_info.header_unions[type_spec.header_union.name]
        case "header_stack":
            result = P4HeaderStackType(type_spec.header_stack, type_info)
        case "header_union_stack":
            result = P4HeaderUnionStackType(type_spec.header_union_stack, type_info)
        case "new_type":
            result = type_info.new_types[type_spec.new_type.name]
        # TODO: "enum", "error", "serializable_enum"
        case other:
            raise ValueError(f"unknown type_spec: {other!r}")
    return result


class P4Register(_P4TopLevel[p4i.Register]):
    "Represents Register in schema."

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
    "Represents Digest in schema."

    _type_spec: _P4Type

    def _finish_init(self, defs: _P4Defs):
        self._type_spec = _parse_type_spec(self.pbuf.type_spec, defs.type_info)

    @property
    def type_spec(self) -> _P4Type:
        return self._type_spec


class P4ValueSet(_P4TopLevel[p4i.ValueSet]):
    "Represents ValueSet in schema."

    _match: P4EntityMap[P4MatchField]

    def __init__(self, pbuf: p4i.ValueSet):
        super().__init__(pbuf)
        self._match = P4EntityMap[P4MatchField]("match field")

        for field in self.pbuf.match:
            self._match._add(P4MatchField(field))

    def _finish_init(self, defs: _P4Defs):
        for field in self._match:
            field._finish_init(defs)

    @property
    def match(self):
        return self._match

    @property
    def size(self) -> int:
        return self.pbuf.size


def _make_alias(name: str) -> str:
    return name.split(".")[-1]


def _check_id(ident: int, entity_type: str) -> bool:
    "Return true if ID belongs to the specified entity type."
    id_prefix = getattr(p4i.P4Ids.Prefix, entity_type.upper())
    return (ident >> 24) == id_prefix


class P4SchemaDescription:
    "Helper class to produce text description of a P4Schema."

    HORIZ_LINE = "\U000023AF"  # Horizontal line
    TABLE = "\U0001F4CB"  # Clipboard
    PROFILE = "\U0001F4E6"  # Package
    PACKET_METADATA = "\U0001f4ec"  # Mailbox
    DIGEST = "\U0001f4c7"  # Card index
    TIMEOUT = "\U000023f1"  # Stopwatch
    CONST = "\U0001f512"  # Closed Lock
    COUNTER = "\U0001f4c8"  # Chart
    METER = "\U0001f6a6"  # Stoplight
    REGISTER = "\U0001f5c3"  # Card file box
    TABLE_ONLY = "\U00002191"  # Up arrow
    DEFAULT_ONLY = "\U00002193"  # Down arrow

    MATCH_TYPES = {
        P4MatchType.EXACT: ":",
        P4MatchType.LPM: "/",
        P4MatchType.TERNARY: "/&",
        P4MatchType.RANGE: "..",
        P4MatchType.OPTIONAL: "?",
    }

    def __init__(self, schema: P4Schema):
        self._schema = schema

    def __str__(self) -> str:
        result = self._describe_preamble()
        for table in self._schema.tables:
            result += self._describe_table(table)
        for profile in self._schema.action_profiles:
            result += self._describe_profile(profile)
        for counter in self._schema.counters:
            result += self._describe_counter(counter)
        for metadata in self._schema.controller_packet_metadata:
            result += self._describe_packet_metadata(metadata)
        for digest in self._schema.digests:
            result += self._describe_digest(digest)
        return result

    def _describe_preamble(self) -> str:
        "Describe preamble."

        sch = self._schema
        name = sch.name
        if not name:
            name = "<Unnamed>"

        preamble = f"\n{name} (version={sch.version}, arch={sch.arch})\n"
        preamble += self.HORIZ_LINE * (len(preamble) - 3) + "\n"
        return preamble

    def _describe_match_type(self, match_type: P4MatchType | str):
        "Return a string describing the match type."

        if isinstance(match_type, str):
            return f"[{match_type}]"
        return self.MATCH_TYPES[match_type]

    def _describe_table(self, table: P4Table) -> str:
        "Describe P4Table."

        # Table header
        const = self.CONST if table.is_const else ""
        line = f"{self.TABLE} {table.alias}[{table.size}]{const}"
        if table.action_profile:
            line += f" -> {self._describe_profile_brief(table.action_profile)}"
        line += "\n"

        # Table fields
        line += "   "
        for field in table.match_fields:
            match_type = self._describe_match_type(field.match_type)
            line += f"{field.alias}{match_type}{field.bitwidth} "
        line += "\n"

        # Table actions
        line += "   "
        line += " ".join(self._describe_action(action) for action in table.actions)
        line += "\n"

        flags = self._describe_table_flags(table)
        if flags:
            line += "   " + flags + "\n"

        return line

    def _describe_table_flags(self, table: P4Table) -> str:
        "Describe additional table flags."
        flags = list[str]()

        if table.idle_timeout_behavior != P4IdleTimeoutBehavior.NO_TIMEOUT:
            flags.append(f"{self.TIMEOUT} {table.idle_timeout_behavior.name.lower()}")

        if table.direct_counter:
            flags.append(
                f"{self.COUNTER}counter-{table.direct_counter.unit.name.lower()}"
            )

        if table.direct_meter:
            flags.append(f"{self.METER}meter")  # FIXME: more info?

        if table.const_default_action:
            flags.append(f"{self.CONST}{table.const_default_action.alias}()")

        return ", ".join(flags)

    def _describe_profile_brief(self, profile: P4ActionProfile) -> str:
        "Describe P4ActionProfile briefly when linked to table."

        return f"{self.PROFILE} {profile.alias}[{profile.size}]"

    def _describe_profile(self, profile: P4ActionProfile) -> str:
        "Describe P4ActionProfile."

        opts = list[str]()
        if profile.with_selector:
            opts.append("type=selector")
            opts.append(f"max_group_size={profile.max_group_size}")
        else:
            opts.append("type=profile")

        table_names = ",".join(profile.table_names)
        opts.append(f"tables={table_names}")

        line = self._describe_profile_brief(profile)
        line += f"\n   {' '.join(opts)}\n"

        return line

    def _describe_action(self, action: P4ActionRef):
        "Describe P4ActionRef."
        params = ", ".join(f"{p.name}:{p.bitwidth}" for p in action.params)
        match action.scope:
            case P4ActionScope.TABLE_ONLY:
                scope = self.TABLE_ONLY
            case P4ActionScope.DEFAULT_ONLY:
                scope = self.DEFAULT_ONLY
            case _:
                scope = ""
        return f"{scope}{action.alias}({params})"

    def _describe_packet_metadata(self, metadata: P4ControllerPacketMetadata):
        "Describe P4ControllerPacketMetadata."
        line = f"{self.PACKET_METADATA} {metadata.alias}\n   "
        for mdata in metadata.metadata:
            line += f"{mdata.name}:{mdata.bitwidth} "
        line += "\n"

        return line

    def _describe_digest(self, digest: P4Digest):
        "Describe P4Digest."
        line = f"{self.DIGEST} {digest.alias}\n   "
        line += self._describe_typespec(digest.type_spec)
        line += "\n"

        return line

    def _describe_typespec(self, type_spec: _P4Type):
        "Describe P4TypeInfo."
        match type_spec:
            case P4StructType():
                return " ".join(
                    [
                        f"{key}:{self._describe_p4type(value)}"
                        for key, value in type_spec.members.items()
                    ]
                )
            case _:
                return "unsupported: {type_spec!r}"

    def _describe_p4type(self, atype: _P4Type):
        "Describe _P4Type value."
        match atype:
            case P4BitsType():
                return f"{atype.bitwidth}"
            case _:
                return "<unsupported>"

    def _describe_counter(self, counter: P4Counter):
        "Describe P4Counter."
        line = f"{self.COUNTER} {counter.alias}[{counter.size}]: {counter.unit.name.lower()}\n"
        return line

    def _describe_register(self, register: P4Register):
        "Describe P4Register."
        line = f"{self.REGISTER} {register.alias}[{register.size}]: {self._describe_typespec(register.type_spec)}"
        return line


_EMPTY_P4DEFS = _P4Defs(p4i.P4Info())
