"Implements entity encode/decode functions."

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

import abc
import collections.abc
from dataclasses import KW_ONLY, dataclass
from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    NoReturn,
    Protocol,
    Sequence,
    TypeVar,
)

from typing_extensions import Self

from finsy import p4values, pbutil
from finsy.log import LOGGER
from finsy.p4schema import (
    P4Action,
    P4ActionRef,
    P4Schema,
    P4Table,
    P4UpdateType,
    P4ValueSet,
)
from finsy.proto import p4r


class _SupportsDecodeEntity(Protocol):
    @classmethod
    def decode(
        cls,
        msg: Any,  # (p4r.Entity | p4r.StreamMessageResponse)
        schema: P4Schema,
    ) -> Self:
        "Decode message to produce entity or stream response."
        ...  # pragma: no cover


class _SupportsEncodeEntity(Protocol):
    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode object as an entity."
        ...  # pragma: no cover


class _SupportsEncodeUpdate(Protocol):
    def encode_update(self, schema: P4Schema) -> p4r.Update | p4r.StreamMessageRequest:
        "Encode object as an update or stream request."
        ...  # pragma: no cover


_DECODER: dict[str, _SupportsDecodeEntity] = {}

_D = TypeVar("_D", bound=_SupportsDecodeEntity)


def decodable(key: str) -> Callable[[_D], _D]:
    "Class decorator to specify the class used to decode P4Runtime messages."

    def _decorate(cls: _D) -> _D:
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
        sub_msg = msg.packet_replication_engine_entry
        key = sub_msg.WhichOneof("type")
        if key is None:
            raise ValueError("missing packet_replication_engine type")

    return _DECODER[key].decode(msg, schema)


def decode_stream(msg: p4r.StreamMessageResponse, schema: P4Schema) -> Any:
    "Decode a StreamMessageResponse to the class registered in _DECODER."
    key = msg.WhichOneof("update")
    if key is None:
        raise ValueError("missing update")

    return _DECODER[key].decode(msg, schema)


# Recursive type vars.
P4EntityList = p4r.Entity | _SupportsEncodeEntity | Iterable["P4EntityList"]
P4UpdateList = (
    p4r.Update
    | p4r.StreamMessageRequest
    | _SupportsEncodeUpdate
    | Iterable["P4UpdateList"]
)


def flatten(values: Any) -> Iterator[Any]:
    "Flatten lists and tuples."
    for val in values:
        if isinstance(val, collections.abc.Iterable):
            yield from flatten(val)
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


def encode_entities(
    values: Iterable[P4EntityList], schema: P4Schema
) -> list[p4r.Entity]:
    """Convert list of python objects to list of P4Runtime Entities."""
    return [_encode_entity(val, schema) for val in flatten(values)]


def _encode_update(
    value: p4r.Update | p4r.StreamMessageRequest | _SupportsEncodeUpdate,
    schema: P4Schema,
) -> p4r.Update | p4r.StreamMessageRequest:
    "Encode an Update or outgoing message request, if necessary."
    if isinstance(value, (p4r.Update, p4r.StreamMessageRequest)):
        return value

    return value.encode_update(schema)


def encode_updates(
    values: P4UpdateList,
    schema: P4Schema,
) -> list[p4r.Update | p4r.StreamMessageRequest]:
    """Convert list of python objects to P4Runtime Updates or request messages."""
    if not isinstance(values, collections.abc.Iterable):
        return [_encode_update(values, schema)]

    return [_encode_update(val, schema) for val in flatten(values)]


class P4Entity(abc.ABC):
    """Abstract base class for P4Entity subclasses.

    All entities have `encode` and `decode` methods.

    The `encode` method is used to encode the entity to a Protobuf message. The
    `decode` method is a class method that decodes a Protobuf message and
    returns the entity object.
    """

    @abc.abstractmethod
    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode object as an entity."

    @classmethod
    @abc.abstractmethod
    def decode(cls, msg: p4r.Entity, schema: P4Schema) -> Self:
        "Decode Protobuf to entity object."


class _P4Writable(P4Entity):
    """Abstract base class for entities that support insert/modify/delete.

    A writable entity can specify the type of update by using a unary operator.

    1. `+` means INSERT.
    2. `-` means DELETE.
    3. `~` means MODIFY.

    Note: For efficiency, this class just mutates itself! This is safe as long
    as entities are used only once.
    """

    _update_type: P4UpdateType = P4UpdateType.UNSPECIFIED

    def __pos__(self) -> Self:
        if self._update_type != P4UpdateType.UNSPECIFIED:
            raise ValueError(f"update type already specified")
        self._update_type = P4UpdateType.INSERT
        return self

    def __neg__(self) -> Self:
        if self._update_type != P4UpdateType.UNSPECIFIED:
            raise ValueError(f"update type already specified")
        self._update_type = P4UpdateType.DELETE
        return self

    def __invert__(self) -> Self:
        if self._update_type != P4UpdateType.UNSPECIFIED:
            raise ValueError(f"update type already specified")
        self._update_type = P4UpdateType.MODIFY
        return self

    def encode_update(self, schema: P4Schema) -> p4r.Update:
        "Encode object as a Protobuf Update message."
        if self._update_type == P4UpdateType.UNSPECIFIED:
            raise ValueError(f"unspecified update type (+, ~, -): {self!r}")
        return p4r.Update(type=self._update_type.vt(), entity=self.encode(schema))


class _P4ModifyOnly(P4Entity):
    """Abstract base class for entities that only support modify.

    You can use `~` to indicate MODIFY, but this is optional.
    """

    def __invert__(self) -> Self:
        return self

    def encode_update(self, schema: P4Schema) -> p4r.Update:
        "Encode object as a Protobuf Update message."
        return p4r.Update(type=P4UpdateType.MODIFY.vt(), entity=self.encode(schema))


_DataValueType = Any  # TODO: tighten P4Data type constraint later
_MetadataDictType = dict[str, Any]
_PortType = int
_ReplicaCanonType = tuple[_PortType, int]
_ReplicaType = _ReplicaCanonType | _PortType

P4Weight = int | tuple[int, int]
P4WeightedAction = tuple[P4Weight, "P4TableAction"]


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


def format_replica(value: _ReplicaType) -> str:
    "Format python representation of Replica."
    if isinstance(value, int):
        return str(value)
    assert isinstance(value, tuple) and len(value) == 2
    port, instance = value
    if instance == 0:
        return str(port)
    return f"{port}#{instance}"


def encode_watch_port(watch_port: int) -> bytes:
    "Encode watch_port into protobuf message."
    return p4values.encode_exact(watch_port, 32)


def decode_watch_port(watch_port: bytes) -> int:
    "Decode watch_port from protobuf message."
    return int(p4values.decode_exact(watch_port, 32))


class P4TableMatch(dict[str, Any]):
    """Represents a set of P4Runtime field matches.

    Each match field is stored as a dictionary key, where the key is the name
    of the match field. The field's value should be appropriate for the type
    of match (EXACT, LPM, TERNARY, etc.)

    You will construct a match the same as any dictionary.

    Example:
    ```
    # Keyword arguments:
    match = P4TableMatch(ipv4_dst="10.0.0.1")

    # Dictionary argument:
    match = P4TableMatch({"ipv4_dst": "10.0.0.1"})

    # List of 2-tuples:
    match = P4TableMatch([("ipv4_dst", "10.0.0.1")])
    ```

    P4TableMatch is implemented as a subclass of `dict`. It supports all of the
    standard dictionary methods:
    ```
    match = P4TableMatch()
    match["ipv4_dst"] = "10.0.0.1"
    assert len(match) == 1
    ```

    Reference "9.1.1 Match Format":
        Each match field is translated to a FieldMatch Protobuf message by
        translating the entry key to a `field_id`. The type of match (EXACT,
        LPM, TERNARY, OPTIONAL, or RANGE) is determined by the P4Info, and the
        value is converted to the Protobuf representation.

    Supported String Values:
    ```
    EXACT: "255", "0xFF", "10.0.0.1", "2000::1", "00:00:00:00:00:01"

    LPM: "255/8", "0xFF/8", "10.0.0.1/32", "2000::1/128",
            "00:00:00:00:00:01/48"
        (+ all exact formats are promoted to all-1 masks)

    TERNARY: "255/&255", "0xFF/&0xFF", "10.0.0.1/&255.255.255.255",
        "2000::1/&128", "00:00:00:00:00:01/&48"
        (+ all exact formats are promoted to all-1 masks)
        (+ all lpm formats are promoted to the specified contiguous mask)

    RANGE: "0...255", "0x00...0xFF", "10.0.0.1...10.0.0.9",
        "2000::1...2001::9", "00:00:00:00:00:01...00:00:00:00:00:09"
        (+ all exact formats are promoted to single-value ranges)

    OPTIONAL: Same as exact format.
    ```

    See the `p4values.py` module for all supported value classes.

    TODO:
        - Change range delimiter to '-' (and drop '-' delimited MAC's).
        - Consider supporting ternary values with just '/' (and drop support
          for decimal masks; mask must be hexadecimal number).

    See Also:
        - P4TableEntry
    """

    def encode(self, table: P4Table) -> list[p4r.FieldMatch]:
        "Encode TableMatch data as a list of Protobuf fields."
        result: list[p4r.FieldMatch] = []
        match_fields = table.match_fields

        for key, value in self.items():
            try:
                field = match_fields[key].encode_field(value)
                if field is not None:
                    result.append(field)
            except Exception as ex:
                raise ValueError(f"{table.name!r}: Match field {key!r}: {ex}") from ex

        return result

    @classmethod
    def decode(cls, msgs: Iterable[p4r.FieldMatch], table: P4Table) -> Self:
        "Decode Protobuf fields as TableMatch data."
        result = {}
        match_fields = table.match_fields

        for field in msgs:
            fld = match_fields[field.field_id]
            result[fld.alias] = fld.decode_field(field)

        return cls(result)

    def format_dict(
        self,
        table: P4Table,
        *,
        wildcard: str | None = None,
    ) -> dict[str, str]:
        """Format the table match fields as a human-readable dictionary.

        The result is a dictionary showing the TableMatch data for fields
        included in the match. If `wildcard` is specified, all fields defined
        in P4Info will be included with their value set to the wildcard string.

        Values are formatted using the format/type specified in P4Info.
        """
        result: dict[str, str] = {}

        for fld in table.match_fields:
            value = self.get(fld.alias, None)
            if value is not None:
                result[fld.alias] = fld.format_field(value)
            elif wildcard is not None:
                result[fld.alias] = wildcard

        return result

    def format_str(
        self,
        table: P4Table,
        *,
        wildcard: str | None = None,
    ) -> str:
        """Format the table match fields as a human-readable string.

        The result is a string showing the TableMatch data for fields included
        in the match. If `wildcard` is specified, all fields defined in P4Info
        will be included with their value set to the wildcard string.

        All fields are formatted as "name=value" and they are delimited by
        spaces.

        Values are formatted using the format/type specified in P4Info.
        """
        result: list[str] = []

        for fld in table.match_fields:
            value = self.get(fld.alias, None)
            if value is not None:
                result.append(f"{fld.alias}={fld.format_field(value)}")
            elif wildcard is not None:
                result.append(f"{fld.alias}={wildcard}")

        return " ".join(result)


@dataclass(init=False, slots=True)
class P4TableAction:
    """Represents a P4Runtime Action reference for a direct table.

    Attributes:
        name (str): the name of the action.
        args (dict[str, Any]): the action's arguments as a dictionary.

    Example:
        If the name of the action is "ipv4_forward" and it takes a single
        "port" parameter, you can construct the action as:

        ```
        action = P4TableAction("ipv4_forward", port=1)
        ```

    Reference "9.1.2 Action Specification":
        The Action Protobuf has fields: (action_id, params). Finsy translates
        `name` to the appropriate `action_id` as determined by P4Info. It also
        translates each named argument in `args` to the appropriate `param_id`.

    See Also:
        To specify an action for an indirect table, use `P4IndirectAction`.
        Note that P4TableAction will automatically be promoted to an "indirect"
        action if needed.

    Operators:
        A `P4TableAction` supports the multiplication operator (*) for
        constructing "weighted actions". A weighted action is used in specifying
        indirect actions. Here is an action with a weight of 3:

        ```
        weighted_action = 3 * P4TableAction("ipv4_forward", port=1)
        ```

        To specify a weight with a `watch_port`, use a tuple `(weight, port)`.
        The weight is always a positive integer.

    See Also:
        - P4TableEntry
    """

    name: str
    "The name of the action."
    args: dict[str, Any]
    "The action's arguments as a dictionary."

    def __init__(self, __name: str, /, **args: Any):
        self.name = __name
        self.args = args

    def encode_table_action(self, table: P4Table) -> p4r.TableAction:
        """Encode TableAction data as protobuf.

        If the table is indirect, promote the action to a "one-shot" indirect
        action.
        """
        try:
            action = table.actions[self.name]
        except Exception as ex:
            raise ValueError(f"{table.name!r}: {ex}") from ex

        action_p4 = self._encode_action(action)

        if table.action_profile is not None:
            # Promote action to ActionProfileActionSet entry with weight=1.
            return p4r.TableAction(
                action_profile_action_set=p4r.ActionProfileActionSet(
                    action_profile_actions=[
                        p4r.ActionProfileAction(action=action_p4, weight=1)
                    ]
                )
            )

        return p4r.TableAction(action=action_p4)

    def _fail_missing_params(self, action: P4ActionRef | P4Action) -> NoReturn:
        "Report missing parameters."
        seen = {param.name for param in action.params}
        for name in self.args:
            param = action.params[name]
            seen.remove(param.name)

        raise ValueError(f"Action {action.alias!r}: missing parameters {seen}")

    def encode_action(self, schema: P4Schema | P4Table) -> p4r.Action:
        "Encode Action data as protobuf."
        action = schema.actions[self.name]
        return self._encode_action(action)

    def _encode_action(self, action: P4ActionRef | P4Action) -> p4r.Action:
        "Helper to encode an action."
        aps = action.params
        try:
            params = [
                aps[name].encode_param(value) for name, value in self.args.items()
            ]
        except ValueError as ex:
            raise ValueError(f"{action.alias!r}: {ex}") from ex

        # Check for missing action parameters. We always accept an action with
        # no parameters (for wildcard ReadRequests).
        param_count = len(params)
        if param_count > 0 and param_count != len(aps):
            self._fail_missing_params(action)

        return p4r.Action(action_id=action.id, params=params)

    @classmethod
    def decode_table_action(
        cls, msg: p4r.TableAction, table: P4Table
    ) -> Self | "P4IndirectAction":
        "Decode protobuf to TableAction data."
        match msg.WhichOneof("type"):
            case "action":
                return cls.decode_action(msg.action, table)
            case "action_profile_member_id":
                return P4IndirectAction(member_id=msg.action_profile_member_id)
            case "action_profile_group_id":
                return P4IndirectAction(group_id=msg.action_profile_group_id)
            case "action_profile_action_set":
                return P4IndirectAction.decode_action_set(
                    msg.action_profile_action_set, table
                )
            case other:
                raise ValueError(f"unknown oneof: {other!r}")

    @classmethod
    def decode_action(cls, msg: p4r.Action, parent: P4Schema | P4Table) -> Self:
        "Decode protobuf to Action data."
        action = parent.actions[msg.action_id]
        args = {}
        for param in msg.params:
            action_param = action.params[param.param_id]
            value = action_param.decode_param(param)
            args[action_param.name] = value

        return cls(action.alias, **args)

    def format_str(self, schema: P4Schema | P4Table) -> str:
        """Format the table action as a human-readable string.

        The result is formatted to look like a function call:

        ```
        name(param1=value1, ...)
        ```

        Where `name` is the action name, and `(param<N>, value<N>)` are the
        action parameters. The format of `value<N>` is schema-dependent.
        """
        aps = schema.actions[self.name].params
        args = [
            f"{key}={aps[key].format_param(value)}" for key, value in self.args.items()
        ]

        return f"{self.name}({', '.join(args)})"

    def __mul__(self, weight: P4Weight) -> P4WeightedAction:
        "Make a weighted action."
        if not isinstance(
            weight, (int, tuple)
        ):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise NotImplementedError("expected P4Weight")
        return (weight, self)

    def __rmul__(self, weight: P4Weight) -> P4WeightedAction:
        "Make a weighted action."
        if not isinstance(
            weight, (int, tuple)
        ):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise NotImplementedError("expected P4Weight")
        return (weight, self)

    def __call__(self, **params: Any) -> Self:
        "Return a new action with the updated parameters."
        return self.__class__(self.name, **(self.args | params))


@dataclass(slots=True)
class P4IndirectAction:
    """Represents a P4Runtime Action reference for an indirect table.

    An indirect action can be either:

    1. a "one-shot" action (action_set)
    2. a reference to an action profile member (member_id)
    3. a reference to an action profile group (group_id)

    Only one of action_set, member_id or group_id may be configured. The other
    values must be None.

    Attributes:
        action_set: sequence of weighted actions for one-shot
        member_id: ID of action profile member
        group_id: ID of action profile group

    Examples:

    ```python
    # Construct a one-shot action profile.
    one_shot = P4IndirectAction(
        2 * P4TableAction("forward", port=1),
        1 * P4TableAction("forward", port=2),
    )

    # Refer to an action profile member by ID.
    member_action = P4IndirectAction(member_id=1)

    # Refer to an action profile group by ID.
    group_action = P4IndirectAction(group_id=2)
    ```

    References:
        - "9.1.2. Action Specification",
        - "9.2.3. One Shot Action Selector Programming"

    TODO: Refactor into three classes? P4OneShotAction, P4MemberAction, and
        P4GroupAction.

    See Also:
        - P4TableEntry
    """

    action_set: Sequence[P4WeightedAction] | None = None
    "Sequence of weighted actions defining one-shot action profile."
    _: KW_ONLY
    member_id: int | None = None
    "ID of action profile member."
    group_id: int | None = None
    "ID of action profile group."

    def __post_init__(self):
        if not self._check_invariant():
            raise ValueError(
                "exactly one of action_set, member_id, or group_id must be set"
            )

    def _check_invariant(self) -> bool:
        "Return true if instance satisfies class invariant."
        if self.action_set is not None:
            return self.member_id is None and self.group_id is None
        if self.member_id is not None:
            return self.group_id is None
        return self.group_id is not None

    def encode_table_action(self, table: P4Table) -> p4r.TableAction:
        "Encode object as a TableAction."
        if self.action_set is not None:
            return p4r.TableAction(
                action_profile_action_set=self.encode_action_set(table)
            )

        if self.member_id is not None:
            return p4r.TableAction(action_profile_member_id=self.member_id)

        assert self.group_id is not None
        return p4r.TableAction(action_profile_group_id=self.group_id)

    def encode_action_set(self, table: P4Table) -> p4r.ActionProfileActionSet:
        "Encode object as an ActionProfileActionSet."
        assert self.action_set is not None

        profile_actions: list[p4r.ActionProfileAction] = []
        for weight, table_action in self.action_set:
            action = table_action.encode_action(table)

            match weight:
                case int(weight_value):
                    watch_port = None
                case (weight_value, int(watch)):
                    watch_port = encode_watch_port(watch)
                case _:  # pyright: ignore[reportUnnecessaryComparison]
                    raise ValueError(f"unexpected action weight: {weight!r}")

            profile = p4r.ActionProfileAction(action=action, weight=weight_value)
            if watch_port is not None:
                profile.watch_port = watch_port
            profile_actions.append(profile)

        return p4r.ActionProfileActionSet(action_profile_actions=profile_actions)

    @classmethod
    def decode_action_set(cls, msg: p4r.ActionProfileActionSet, table: P4Table) -> Self:
        "Decode ActionProfileActionSet."
        action_set = list[P4WeightedAction]()

        for action in msg.action_profile_actions:
            match action.WhichOneof("watch_kind"):
                case "watch_port":
                    weight = (action.weight, decode_watch_port(action.watch_port))
                case None:
                    weight = action.weight
                case other:
                    # "watch" (deprecated) is not supported
                    raise ValueError(f"unexpected oneof: {other!r}")

            table_action = P4TableAction.decode_action(action.action, table)
            action_set.append((weight, table_action))

        return cls(action_set)

    def format_str(self, table: P4Table) -> str:
        """Format the indirect table action as a human-readable string."""
        if self.action_set is not None:
            weighted_actions = [
                f"{weight}*{action.format_str(table)}"
                for weight, action in self.action_set
            ]
            return " ".join(weighted_actions)

        # Use the name of the action_profile, if we can get it. If not, just
        # use the placeholder "__indirect".
        if table.action_profile is not None:
            profile_name = f"@{table.action_profile.alias}"
        else:
            profile_name = "__indirect"

        if self.member_id is not None:
            return f"{profile_name}[[{self.member_id:#x}]]"

        return f"{profile_name}[{self.group_id:#x}]"

    def __repr__(self) -> str:
        "Customize representation to make it more concise."
        if self.action_set is not None:
            return f"P4IndirectAction(action_set={self.action_set!r})"
        if self.member_id is not None:
            return f"P4IndirectAction(member_id={self.member_id!r})"
        return f"P4IndirectAction(group_id={self.group_id!r})"


@dataclass(kw_only=True, slots=True)
class P4MeterConfig:
    """Represents a P4Runtime MeterConfig.

    Attributes:
        cir (int): Committed information rate (units/sec).
        cburst (int): Committed burst size.
        pir (int): Peak information rate (units/sec).
        pburst (int): Peak burst size.

    Example:
    ```
    config = P4MeterConfig(cir=10, cburst=20, pir=10, pburst=20)
    ```

    See Also:
        - P4TableEntry
        - P4MeterEntry
        - P4DirectMeterEntry
    """

    cir: int
    "Committed information rate (units/sec)."
    cburst: int
    "Committed burst size."
    pir: int
    "Peak information rate (units/sec)."
    pburst: int
    "Peak burst size."

    def encode(self) -> p4r.MeterConfig:
        "Encode object as MeterConfig."
        return p4r.MeterConfig(
            cir=self.cir, cburst=self.cburst, pir=self.pir, pburst=self.pburst
        )

    @classmethod
    def decode(cls, msg: p4r.MeterConfig) -> Self:
        "Decode MeterConfig."
        return cls(cir=msg.cir, cburst=msg.cburst, pir=msg.pir, pburst=msg.pburst)


@dataclass(kw_only=True, slots=True)
class P4CounterData:
    """Represents a P4Runtime object that keeps statistics of bytes and packets.

    Attributes:
        byte_count (int): the number of octets
        packet_count (int): the number of packets

    See Also:
        - P4TableEntry
        - P4MeterCounterData
        - P4CounterEntry
        - P4DirectCounterEntry
    """

    byte_count: int = 0
    "The number of octets."
    packet_count: int = 0
    "The number of packets."

    def encode(self) -> p4r.CounterData:
        "Encode object as CounterData."
        return p4r.CounterData(
            byte_count=self.byte_count, packet_count=self.packet_count
        )

    @classmethod
    def decode(cls, msg: p4r.CounterData) -> Self:
        "Decode CounterData."
        return cls(byte_count=msg.byte_count, packet_count=msg.packet_count)


@dataclass(kw_only=True, slots=True)
class P4MeterCounterData:
    """Represents a P4Runtime MeterCounterData that stores per-color counters.

    Attributes:
        green (CounterData): counter data for packets marked GREEN.
        yellow (CounterData): counter data for packets marked YELLOW.
        red (CounterData): counter data for packets marked RED.

    See Also:
        - P4TableEntry
        - P4MeterEntry
        - P4DirectMeterEntry
    """

    green: P4CounterData
    "Counter of packets marked GREEN."
    yellow: P4CounterData
    "Counter of packets marked YELLOW."
    red: P4CounterData
    "Counter of packets marked RED."

    def encode(self) -> p4r.MeterCounterData:
        "Encode object as MeterCounterData."
        return p4r.MeterCounterData(
            green=self.green.encode(),
            yellow=self.yellow.encode(),
            red=self.red.encode(),
        )

    @classmethod
    def decode(cls, msg: p4r.MeterCounterData) -> Self:
        "Decode MeterCounterData."
        return cls(
            green=P4CounterData.decode(msg.green),
            yellow=P4CounterData.decode(msg.yellow),
            red=P4CounterData.decode(msg.red),
        )


@decodable("table_entry")
@dataclass(slots=True)
class P4TableEntry(_P4Writable):
    """Represents a P4Runtime table entry.

    Attributes:
        table_id (str): Name of the table.
        match (P4TableMatch | None): Entry's match fields.
        action (P4TableAction | P4IndirectAction | None): Entry's action.
        is_default_action (bool): True if entry is the default table entry.
        priority (int): Priority of a table entry when match implies TCAM lookup.
        metadata (bytes): Arbitrary controller cookie (1.2.0).
        controller_metadata (int): Deprecated controller cookie (< 1.2.0).
        meter_config (P4MeterConfig | None): Meter configuration.
        counter_data (P4CounterData | None): Counter data for table entry.
        meter_counter_data (P4MeterCounterData | None): Meter counter data (1.4.0).
        idle_timeout_ns (int): Idle timeout in nanoseconds.
        time_since_last_hit (int | None): Nanoseconds since entry last matched.
        is_const (bool): True if entry is constant (1.4.0).

    The most commonly used fields are table_id, match, action, is_default_action,
    and priority. See the P4Runtime Spec for usage examples regarding the other
    attributes.

    When writing a P4TableEntry, you can specify the type of update using '+',
    '-', and '~'.

    Examples:
    ```
    # Specify all tables when using "read".
    entry = fy.P4TableEntry()

    # Specify the table named "ipv4" when using "read".
    entry = fy.P4TableEntry("ipv4")

    # Specify the default entry in the "ipv4" table when using "read".
    entry = fy.P4TableEntry("ipv4", is_default_action=True)

    # Insert an entry into the "ipv4" table.
    update = +fy.P4TableEntry(
        "ipv4",
        match=fy.Match(ipv4_dst="10.0.0.0/8"),
        action=fy.Action("forward", port=1),
    )

    # Modify the default action in the "ipv4" table.
    update = ~fy.P4TableEntry(
        "ipv4",
        action=fy.Action("forward", port=5),
        is_default_action=True
    )
    ```

    Operators:
        You can retrieve a match field from a table entry using `[]`. For
        example, `entry["ipv4_dst"]` is the same as `entry.match["ipv4_dst"]`.

    Formatting Helpers:
        The `match_str` and `action_str` methods provide P4Info-aware formatting
        of the match and action attributes.
    """

    table_id: str = ""
    "Name of the table."
    _: KW_ONLY
    match: P4TableMatch | None = None
    "Entry's match fields."
    action: P4TableAction | P4IndirectAction | None = None
    "Entry's action."
    is_default_action: bool = False
    "True if entry is the default table entry."
    priority: int = 0
    "Priority of a table entry when match implies TCAM lookup."
    metadata: bytes = b""
    "Arbitrary controller cookie. (1.2.0)."
    controller_metadata: int = 0
    "Deprecated controller cookie (< 1.2.0)."
    meter_config: P4MeterConfig | None = None
    "Meter configuration."
    counter_data: P4CounterData | None = None
    "Counter data for table entry."
    meter_counter_data: P4MeterCounterData | None = None
    "Meter counter data (1.4.0)."
    idle_timeout_ns: int = 0
    "Idle timeout in nanoseconds."
    time_since_last_hit: int | None = None
    "Nanoseconds since entry last matched."
    is_const: bool = False
    "True if entry is constant (1.4.0)."

    def __getitem__(self, key: str) -> Any:
        "Convenience accessor to retrieve a value from the `match` property."
        if self.match is not None:
            return self.match[key]
        raise KeyError(key)

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode TableEntry data as protobuf."
        return p4r.Entity(table_entry=self.encode_entry(schema))

    def encode_entry(self, schema: P4Schema) -> p4r.TableEntry:
        "Encode TableEntry data as protobuf."
        if not self.table_id:
            return self._encode_empty()

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
            controller_metadata=self.controller_metadata,
            meter_config=meter_config,
            counter_data=counter_data,
            meter_counter_data=meter_counter_data,
            is_default_action=self.is_default_action,
            idle_timeout_ns=self.idle_timeout_ns,
            time_since_last_hit=time_since_last_hit,
            metadata=self.metadata,
            is_const=self.is_const,
        )

    def _encode_empty(self) -> p4r.TableEntry:
        "Encode an empty wildcard request."
        if self.counter_data is not None:
            counter_data = self.counter_data.encode()
        else:
            counter_data = None

        # FIXME: time_since_last_hit not supported for wildcard reads?
        if self.time_since_last_hit is not None:
            time_since_last_hit = p4r.TableEntry.IdleTimeout(
                elapsed_ns=self.time_since_last_hit
            )
        else:
            time_since_last_hit = None

        return p4r.TableEntry(
            counter_data=counter_data,
            time_since_last_hit=time_since_last_hit,
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

        if entry.HasField("counter_data"):
            counter_data = P4CounterData.decode(entry.counter_data)
        else:
            counter_data = None

        if entry.HasField("meter_counter_data"):
            meter_counter_data = P4MeterCounterData.decode(entry.meter_counter_data)
        else:
            meter_counter_data = None

        return cls(
            table_id=table.alias,
            match=match,
            action=action,
            priority=entry.priority,
            controller_metadata=entry.controller_metadata,
            meter_config=meter_config,
            counter_data=counter_data,
            meter_counter_data=meter_counter_data,
            is_default_action=entry.is_default_action,
            idle_timeout_ns=entry.idle_timeout_ns,
            time_since_last_hit=last_hit,
            metadata=entry.metadata,
            is_const=entry.is_const,
        )

    def match_dict(
        self,
        schema: P4Schema | None = None,
        *,
        wildcard: str | None = None,
    ) -> dict[str, str]:
        """Format the match fields as a dictionary of strings.

        If `wildcard` is None, only include match fields that have values. If
        `wildcard` is set, include all field names but replace unset values with
        given wildcard value (e.g. "*")
        """
        if schema is None:
            schema = P4Schema.current()
        table = schema.tables[self.table_id]
        if self.match is not None:
            return self.match.format_dict(table, wildcard=wildcard)
        return P4TableMatch().format_dict(table, wildcard=wildcard)

    def match_str(
        self,
        schema: P4Schema | None = None,
        *,
        wildcard: str | None = None,
    ) -> str:
        "Format the match fields as a human-readable, canonical string."
        if schema is None:
            schema = P4Schema.current()
        table = schema.tables[self.table_id]
        if self.match is not None:
            return self.match.format_str(table, wildcard=wildcard)
        return P4TableMatch().format_str(table, wildcard=wildcard)

    def action_str(self, schema: P4Schema | None = None) -> str:
        "Format the actions as a human-readable, canonical string."
        if schema is None:
            schema = P4Schema.current()
        table = schema.tables[self.table_id]
        if self.action is None:
            return "NoAction()"
        return self.action.format_str(table)


@decodable("register_entry")
@dataclass(slots=True)
class P4RegisterEntry(_P4ModifyOnly):
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
            return cls()

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
@dataclass(slots=True)
class P4MulticastGroupEntry(_P4Writable):
    "Represents a P4Runtime MulticastGroupEntry."

    multicast_group_id: int = 0
    _: KW_ONLY
    replicas: Sequence[_ReplicaType] = ()
    metadata: bytes = b""

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode MulticastGroupEntry data as protobuf."
        entry = p4r.MulticastGroupEntry(
            multicast_group_id=self.multicast_group_id,
            replicas=[encode_replica(replica) for replica in self.replicas],
            metadata=self.metadata,
        )
        return p4r.Entity(
            packet_replication_engine_entry=p4r.PacketReplicationEngineEntry(
                multicast_group_entry=entry
            )
        )

    @classmethod
    def decode(cls, msg: p4r.Entity, schema: P4Schema) -> Self:
        "Decode protobuf to MulticastGroupEntry data."
        entry = msg.packet_replication_engine_entry.multicast_group_entry
        return cls(
            multicast_group_id=entry.multicast_group_id,
            replicas=tuple(decode_replica(replica) for replica in entry.replicas),
            metadata=entry.metadata,
        )

    def replicas_str(self) -> str:
        "Format the replicas as a human-readable, canonical string."
        return " ".join(format_replica(rep) for rep in self.replicas)


@decodable("clone_session_entry")
@dataclass(slots=True)
class P4CloneSessionEntry(_P4Writable):
    "Represents a P4Runtime CloneSessionEntry."

    session_id: int = 0
    _: KW_ONLY
    class_of_service: int = 0
    packet_length_bytes: int = 0
    replicas: Sequence[_ReplicaType] = ()

    def encode(self, schema: P4Schema) -> p4r.Entity:
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
    def decode(cls, msg: p4r.Entity, schema: P4Schema) -> Self:
        "Decode protobuf to CloneSessionEntry data."
        entry = msg.packet_replication_engine_entry.clone_session_entry
        return cls(
            session_id=entry.session_id,
            class_of_service=entry.class_of_service,
            packet_length_bytes=entry.packet_length_bytes,
            replicas=tuple(decode_replica(replica) for replica in entry.replicas),
        )

    def replicas_str(self) -> str:
        "Format the replicas as a human-readable, canonical string."
        return " ".join(format_replica(rep) for rep in self.replicas)


@decodable("digest_entry")
@dataclass(slots=True)
class P4DigestEntry(_P4Writable):
    "Represents a P4Runtime DigestEntry."

    digest_id: str = ""
    _: KW_ONLY
    max_list_size: int = 0
    max_timeout_ns: int = 0
    ack_timeout_ns: int = 0

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode DigestEntry data as protobuf."
        if not self.digest_id:
            return p4r.Entity(digest_entry=p4r.DigestEntry())

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
        if entry.digest_id == 0:
            return cls()

        digest = schema.digests[entry.digest_id]

        config = entry.config
        return cls(
            digest.alias,
            max_list_size=config.max_list_size,
            max_timeout_ns=config.max_timeout_ns,
            ack_timeout_ns=config.ack_timeout_ns,
        )


@decodable("action_profile_member")
@dataclass(slots=True)
class P4ActionProfileMember(_P4Writable):
    "Represents a P4Runtime ActionProfileMember."

    action_profile_id: str = ""
    _: KW_ONLY
    member_id: int = 0
    action: P4TableAction | None = None

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode P4ActionProfileMember as protobuf."
        if not self.action_profile_id:
            return p4r.Entity(action_profile_member=p4r.ActionProfileMember())

        profile = schema.action_profiles[self.action_profile_id]

        if self.action:
            action = self.action.encode_action(schema)
        else:
            action = None

        entry = p4r.ActionProfileMember(
            action_profile_id=profile.id,
            member_id=self.member_id,
            action=action,
        )
        return p4r.Entity(action_profile_member=entry)

    @classmethod
    def decode(cls, msg: p4r.Entity, schema: P4Schema) -> Self:
        "Decode protobuf to ActionProfileMember data."
        entry = msg.action_profile_member
        if entry.action_profile_id == 0:
            return cls()

        profile = schema.action_profiles[entry.action_profile_id]

        if entry.HasField("action"):
            action = P4TableAction.decode_action(entry.action, schema)
        else:
            action = None

        return cls(
            action_profile_id=profile.alias,
            member_id=entry.member_id,
            action=action,
        )

    def action_str(self) -> str:
        "Return string representation of action."
        if not self.action:
            return ""
        schema = P4Schema.current()
        return self.action.format_str(schema)


@dataclass(slots=True)
class P4Member:
    """Represents an ActionProfileGroup Member.

    See Also:
        - P4ActionProfileGroup
    """

    member_id: int
    _: KW_ONLY
    weight: P4Weight

    def encode(self) -> p4r.ActionProfileGroup.Member:
        "Encode P4Member as protobuf."
        match self.weight:
            case int(weight):
                watch_port = None
            case (int(weight), int(watch)):
                watch_port = encode_watch_port(watch)
            case other:  # pyright: ignore[reportUnnecessaryComparison]
                raise ValueError(f"unexpected weight: {other!r}")

        member = p4r.ActionProfileGroup.Member(
            member_id=self.member_id,
            weight=weight,
        )

        if watch_port is not None:
            member.watch_port = watch_port
        return member

    @classmethod
    def decode(cls, msg: p4r.ActionProfileGroup.Member) -> Self:
        "Decode protobuf to P4Member."
        match msg.WhichOneof("watch_kind"):
            case "watch_port":
                weight = (msg.weight, decode_watch_port(msg.watch_port))
            case None:
                weight = msg.weight
            case other:
                # "watch" (deprecated) is not supported
                raise ValueError(f"unknown oneof: {other!r}")

        return cls(member_id=msg.member_id, weight=weight)


@decodable("action_profile_group")
@dataclass(slots=True)
class P4ActionProfileGroup(_P4Writable):
    "Represents a P4Runtime ActionProfileGroup."

    action_profile_id: str = ""
    _: KW_ONLY
    group_id: int = 0
    max_size: int = 0
    members: Sequence[P4Member] | None = None

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode P4ActionProfileGroup as protobuf."
        if not self.action_profile_id:
            return p4r.Entity(action_profile_group=p4r.ActionProfileGroup())

        profile = schema.action_profiles[self.action_profile_id]

        if self.members is not None:
            members = [member.encode() for member in self.members]
        else:
            members = None

        entry = p4r.ActionProfileGroup(
            action_profile_id=profile.id,
            group_id=self.group_id,
            members=members,
            max_size=self.max_size,
        )
        return p4r.Entity(action_profile_group=entry)

    @classmethod
    def decode(cls, msg: p4r.Entity, schema: P4Schema) -> Self:
        "Decode protobuf to ActionProfileGroup data."
        entry = msg.action_profile_group
        if entry.action_profile_id == 0:
            return cls()

        profile = schema.action_profiles[entry.action_profile_id]

        if entry.members:
            members = [P4Member.decode(member) for member in entry.members]
        else:
            members = None

        return cls(
            action_profile_id=profile.alias,
            group_id=entry.group_id,
            max_size=entry.max_size,
            members=members,
        )

    def action_str(self) -> str:
        "Return string representation of the weighted members."
        if not self.members:
            return ""

        return " ".join(
            [f"{member.weight}*{member.member_id:#x}" for member in self.members]
        )


@decodable("meter_entry")
@dataclass(slots=True)
class P4MeterEntry(_P4ModifyOnly):
    "Represents a P4Runtime MeterEntry."

    meter_id: str = ""
    _: KW_ONLY
    index: int | None = None
    config: P4MeterConfig | None = None
    counter_data: P4MeterCounterData | None = None

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode P4MeterEntry to protobuf."
        if not self.meter_id:
            return p4r.Entity(meter_entry=p4r.MeterEntry())

        meter = schema.meters[self.meter_id]

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
            meter_id=meter.id,
            index=index,
            config=config,
            counter_data=counter_data,
        )
        return p4r.Entity(meter_entry=entry)

    @classmethod
    def decode(cls, msg: p4r.Entity, schema: P4Schema) -> Self:
        "Decode protobuf to P4MeterEntry."
        entry = msg.meter_entry
        if not entry.meter_id:
            return cls()

        meter = schema.meters[entry.meter_id]

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
            meter_id=meter.alias,
            index=index,
            config=config,
            counter_data=counter_data,
        )


@decodable("direct_meter_entry")
@dataclass(kw_only=True, slots=True)
class P4DirectMeterEntry(_P4ModifyOnly):
    "Represents a P4Runtime DirectMeterEntry."

    table_entry: P4TableEntry | None = None
    config: P4MeterConfig | None = None
    counter_data: P4MeterCounterData | None = None

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode P4DirectMeterEntry as protobuf."
        if self.table_entry is not None:
            table_entry = self.table_entry.encode_entry(schema)
        else:
            table_entry = None

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

        if entry.HasField("table_entry"):
            table_entry = P4TableEntry.decode_entry(entry.table_entry, schema)
        else:
            table_entry = None

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
@dataclass(slots=True)
class P4CounterEntry(_P4ModifyOnly):
    "Represents a P4Runtime CounterEntry."

    counter_id: str = ""
    _: KW_ONLY
    index: int | None = None
    data: P4CounterData | None = None

    @property
    def packet_count(self) -> int:
        "Packet count from counter data (or 0 if there is no data)."
        if self.data is not None:
            return self.data.packet_count
        return 0

    @property
    def byte_count(self) -> int:
        "Byte count from counter data (or 0 if there is no data)."
        if self.data is not None:
            return self.data.byte_count
        return 0

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode P4CounterEntry as protobuf."
        if not self.counter_id:
            return p4r.Entity(counter_entry=p4r.CounterEntry())

        counter = schema.counters[self.counter_id]

        if self.index is not None:
            index = p4r.Index(index=self.index)
        else:
            index = None

        if self.data is not None:
            data = self.data.encode()
        else:
            data = None

        entry = p4r.CounterEntry(
            counter_id=counter.id,
            index=index,
            data=data,
        )
        return p4r.Entity(counter_entry=entry)

    @classmethod
    def decode(cls, msg: p4r.Entity, schema: P4Schema) -> Self:
        "Decode protobuf to P4CounterEntry."
        entry = msg.counter_entry
        if not entry.counter_id:
            return cls()

        counter = schema.counters[entry.counter_id]

        if entry.HasField("index"):
            index = entry.index.index
        else:
            index = None

        if entry.HasField("data"):
            data = P4CounterData.decode(entry.data)
        else:
            data = None

        return cls(counter_id=counter.alias, index=index, data=data)


@decodable("direct_counter_entry")
@dataclass(slots=True)
class P4DirectCounterEntry(_P4ModifyOnly):
    "Represents a P4Runtime DirectCounterEntry."

    counter_id: str = ""
    _: KW_ONLY
    table_entry: P4TableEntry | None = None
    data: P4CounterData | None = None

    @property
    def table_id(self) -> str:
        "Return table_id of related table."
        if self.table_entry is None:
            return ""
        return self.table_entry.table_id

    @property
    def packet_count(self) -> int:
        "Packet count from counter data (or 0 if there is no data)."
        if self.data is not None:
            return self.data.packet_count
        return 0

    @property
    def byte_count(self) -> int:
        "Byte count from counter data (or 0 if there is no data)."
        if self.data is not None:
            return self.data.byte_count
        return 0

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode P4DirectCounterEntry as protobuf."
        if self.table_entry is None:
            # Use `counter_id` to construct a `P4TableEntry` with the proper
            # table name.
            if self.counter_id:
                tb_name = schema.direct_counters[self.counter_id].direct_table_name
                table_entry = P4TableEntry(tb_name)
            else:
                table_entry = P4TableEntry()
        else:
            table_entry = self.table_entry

        if self.data is not None:
            data = self.data.encode()
        else:
            data = None

        entry = p4r.DirectCounterEntry(
            table_entry=table_entry.encode_entry(schema),
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

        # Determine `counter_id` from table_entry.
        counter_id = ""
        if table_entry is not None and table_entry.table_id:
            direct_counter = schema.tables[table_entry.table_id].direct_counter
            assert direct_counter is not None
            counter_id = direct_counter.alias

        return cls(counter_id, table_entry=table_entry, data=data)


class P4ValueSetMember(dict[str, Any]):
    """Represents a sequence of P4Runtime FieldMatch in a ValueSet.

    To access an unnamed, singular value, use `member.value`.

    See Also:
        - P4ValueSetEntry
    """

    def __init__(
        self,
        __value: int | dict[str, Any] | None = None,
        **kwds: Any,
    ):
        if __value is None:
            super().__init__(**kwds)
        elif isinstance(__value, int):
            if kwds:
                raise ValueError("invalid keyword arguments")
            super().__init__({"": __value})
        else:
            super().__init__(__value, **kwds)

    @property
    def value(self) -> Any:
        "Return the unnamed, singular value."
        return self[""]

    def encode(self, value_set: P4ValueSet) -> list[p4r.FieldMatch]:
        "Encode P4ValueSetMember data as protobuf."
        result: list[p4r.FieldMatch] = []
        match = value_set.match

        for key, value in self.items():
            try:
                field = match[key].encode_field(value)
                if field is not None:
                    result.append(field)
            except Exception as ex:
                raise ValueError(
                    f"{value_set.name!r}: Match field {key!r}: {ex}"
                ) from ex

        return result

    @classmethod
    def decode(cls, msgs: Iterable[p4r.FieldMatch], value_set: P4ValueSet) -> Self:
        "Decode protobuf to P4ValueSetMember data."
        result = {}
        match = value_set.match

        for field in msgs:
            fld = match[field.field_id]
            result[fld.alias] = fld.decode_field(field)

        return cls(result)


@decodable("value_set_entry")
@dataclass(slots=True)
class P4ValueSetEntry(_P4ModifyOnly):
    "Represents a P4Runtime ValueSetEntry."

    value_set_id: str
    _: KW_ONLY
    members: list[P4ValueSetMember]

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode P4ValueSetEntry as protobuf."
        value_set = schema.value_sets[self.value_set_id]
        members = [
            p4r.ValueSetMember(match=member.encode(value_set))
            for member in self.members
        ]

        return p4r.Entity(
            value_set_entry=p4r.ValueSetEntry(
                value_set_id=value_set.id, members=members
            )
        )

    @classmethod
    def decode(cls, msg: p4r.Entity, schema: P4Schema) -> Self:
        "Decode protobuf to P4ValueSetEntry."
        entry = msg.value_set_entry
        value_set = schema.value_sets[entry.value_set_id]

        members = [
            P4ValueSetMember.decode(member.match, value_set) for member in entry.members
        ]

        return cls(value_set.alias, members=members)


@decodable("packet")
@dataclass(slots=True)
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
            pkt_meta = packet.metadata
            if pkt_meta:
                LOGGER.warning("P4PacketIn unexpected metadata: %r", pkt_meta)
            return cls(packet.payload, metadata={})

        return cls(
            packet.payload,
            metadata=cpm.decode(packet.metadata),
        )

    def __getitem__(self, key: str) -> Any:
        "Retrieve metadata value."
        return self.metadata[key]

    def __repr__(self) -> str:
        "Return friendlier hexadecimal description of packet."
        if self.metadata:
            return f"P4PacketIn(metadata={self.metadata!r}, payload=h'{self.payload.hex()}')"
        return f"P4PacketIn(payload=h'{self.payload.hex()}')"


@dataclass(slots=True)
class P4PacketOut:
    "Represents a P4Runtime PacketOut."

    payload: bytes
    _: KW_ONLY
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

    def __getitem__(self, key: str) -> Any:
        "Retrieve metadata value."
        return self.metadata[key]

    def __repr__(self) -> str:
        "Return friendlier hexadecimal description of packet."
        if self.metadata:
            return f"P4PacketOut(metadata={self.metadata!r}, payload=h'{self.payload.hex()}')"
        return f"P4PacketOut(payload=h'{self.payload.hex()}')"


@decodable("digest")
@dataclass(slots=True)
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

    def __len__(self) -> int:
        "Return number of values in digest list."
        return len(self.data)

    def __getitem__(self, key: int) -> _DataValueType:
        "Retrieve value at given index from digest list."
        return self.data[key]

    def __iter__(self) -> Iterator[_DataValueType]:
        "Iterate over values in digest list."
        return iter(self.data)

    def ack(self) -> "P4DigestListAck":
        "Return the corresponding DigestListAck message."
        return P4DigestListAck(self.digest_id, self.list_id)


@dataclass(slots=True)
class P4DigestListAck:
    "Represents a P4Runtime DigestListAck."

    digest_id: str
    list_id: int

    def encode_update(self, schema: P4Schema) -> p4r.StreamMessageRequest:
        "Encode DigestListAck data as protobuf."
        digest = schema.digests[self.digest_id]

        return p4r.StreamMessageRequest(
            digest_ack=p4r.DigestListAck(
                digest_id=digest.id,
                list_id=self.list_id,
            )
        )


@decodable("idle_timeout_notification")
@dataclass(slots=True)
class P4IdleTimeoutNotification:
    "Represents a P4Runtime IdleTimeoutNotification."

    table_entry: list[P4TableEntry]
    timestamp: int

    @classmethod
    def decode(cls, msg: p4r.StreamMessageResponse, schema: P4Schema) -> Self:
        "Decode protobuf to IdleTimeoutNotification data."
        notification = msg.idle_timeout_notification
        table_entry = [
            P4TableEntry.decode_entry(entry, schema)
            for entry in notification.table_entry
        ]

        return cls(table_entry=table_entry, timestamp=notification.timestamp)

    def __len__(self) -> int:
        "Return number of table entries."
        return len(self.table_entry)

    def __getitem__(self, key: int) -> P4TableEntry:
        "Retrieve table entry at given index."
        return self.table_entry[key]

    def __iter__(self) -> Iterator[P4TableEntry]:
        "Iterate over table entries."
        return iter(self.table_entry)


@decodable("extern_entry")
@dataclass(kw_only=True, slots=True)
class P4ExternEntry(_P4Writable):
    "Represents a P4Runtime ExternEntry."

    extern_type_id: str
    extern_id: str
    entry: pbutil.PBAny

    def encode(self, schema: P4Schema) -> p4r.Entity:
        "Encode ExternEntry data as protobuf."
        extern = schema.externs[self.extern_type_id, self.extern_id]
        entry = p4r.ExternEntry(
            extern_type_id=extern.extern_type_id,
            extern_id=extern.id,
            entry=self.entry,
        )
        return p4r.Entity(extern_entry=entry)

    @classmethod
    def decode(cls, msg: p4r.Entity, schema: P4Schema) -> Self:
        "Decode protobuf to ExternEntry data."
        entry = msg.extern_entry
        extern = schema.externs[entry.extern_type_id, entry.extern_id]
        return cls(
            extern_type_id=extern.extern_type_name,
            extern_id=extern.name,
            entry=entry.entry,
        )
