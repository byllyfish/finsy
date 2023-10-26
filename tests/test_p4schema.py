import difflib
import os
import subprocess
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv4Network
from pathlib import Path

import pytest

from finsy import p4values, pbutil
from finsy.p4schema import (
    P4ActionParam,
    P4BitsType,
    P4BoolType,
    P4EntityMap,
    P4HeaderStackType,
    P4HeaderType,
    P4HeaderUnionStackType,
    P4HeaderUnionType,
    P4MatchField,
    P4MatchType,
    P4NewType,
    P4Schema,
    P4SchemaCache,
    P4StructType,
    P4TupleType,
    P4TypeInfo,
    _parse_type_spec,
)
from finsy.proto import p4i, p4t

P4INFO_TEST_DIR = Path(__file__).parent / "test_data/p4info"


def _coverage():
    "Return true if we are running under coverage."
    return os.environ.get("COVERAGE_RUN", None) is not None


@dataclass
class _Example:
    "Dummy entity used to test P4EntityMap."
    id: int
    name: str
    alias: str


def test_entity_map():
    "Test P4EntityMap helper class."
    example = _Example(1, "example.one", "one")

    entities = P4EntityMap("entry_type")
    assert len(entities) == 0

    entities._add(example)
    assert len(entities) == 1
    assert list(entities) == [example]

    assert entities[1] == example
    assert entities["example.one"] == example
    assert entities["one"] == example

    with pytest.raises(ValueError, match="no entry_type named 'example.zero'"):
        entities["example.zero"]

    assert entities.get(1) == example
    assert entities.get("example.one") == example
    assert entities.get("one") == example
    assert entities.get("zero") is None

    assert repr(entities) == "[_Example(id=1, name='example.one', alias='one')]"


def test_entity_map_split():
    "Test P4EntityMap helper class with split_suffix."
    example = _Example(1, "example.one", "example.one")

    entities = P4EntityMap("entry_type")
    entities._add(example, split_suffix=True)

    assert entities[1] == example
    assert entities["example.one"] == example
    assert entities["one"] == example


def test_entity_map_duplicate():
    "Test P4EntityMap helper class with duplicate entry."
    example1 = _Example(1, "example.one", "example.one")
    example2 = _Example(1, "example.one", "example.one")
    example3 = _Example(2, "example.one", "example.one")

    entities = P4EntityMap("entry_type")
    entities._add(example1)

    with pytest.raises(ValueError, match="id already exists"):
        entities._add(example2)

    with pytest.raises(ValueError, match="name already exists"):
        entities._add(example3)


def test_p4schema():
    "Test P4Schema."
    schema = P4Schema(P4INFO_TEST_DIR / "basic.p4.p4info.txt", b"abc")

    assert schema.p4info is not None
    assert schema.p4blob == b"abc"
    assert repr(schema)
    assert str(schema)


def test_p4info_tables():
    p4 = P4Schema(P4INFO_TEST_DIR / "basic.p4.p4info.txt")

    # Access a table by name.
    ipv4_lpm = p4.tables["MyIngress.ipv4_lpm"]
    assert ipv4_lpm.id == 37375156
    assert ipv4_lpm.name == "MyIngress.ipv4_lpm"
    assert ipv4_lpm.alias == "ipv4_lpm"
    assert ipv4_lpm.brief == ""
    assert ipv4_lpm.description == ""
    assert ipv4_lpm.size == 1024
    assert [field.alias for field in ipv4_lpm._match_fields] == ["dstAddr"]
    assert [action.alias for action in ipv4_lpm._actions] == [
        "ipv4_forward",
        "drop",
        "NoAction",
    ]

    # Test access by alias and ID.
    assert p4.tables["ipv4_lpm"] is ipv4_lpm
    assert p4.tables[37375156] is ipv4_lpm

    # Test table match_fields.
    dstAddr = ipv4_lpm._match_fields["dstAddr"]
    assert dstAddr.match_type == P4MatchType.LPM
    assert dstAddr.bitwidth == 32


def test_p4info_actions():
    p4 = P4Schema(Path(P4INFO_TEST_DIR, "basic.p4.p4info.txt"))

    # Access an action by name.
    noaction = p4.actions["NoAction"]
    assert noaction.id == 21257015
    assert noaction.name == "NoAction"
    assert noaction.alias == "NoAction"
    assert noaction.brief == ""
    assert noaction.description == ""
    assert [anno.name for anno in noaction.annotations] == ["noWarn"]
    assert [anno.body for anno in noaction.annotations] == ['"unused"']

    # Test access by ID.
    assert p4.actions[21257015] is noaction


@pytest.mark.parametrize("p4info_file", P4INFO_TEST_DIR.glob("*.p4info.txt"))
def test_p4info_repr(p4info_file):
    "Test output of P4Schema repr function."
    p4 = P4Schema(p4info_file)

    p4_orig = Path(p4info_file).with_suffix(".repr.txt")
    if p4_orig.exists():
        p4_orig_lines = p4_orig.read_text().splitlines()
    else:
        p4_orig_lines = []

    p4_repr = repr(p4)
    # Skip the rest of this test under code coverage. I'm seeing weird failures
    # in CI, and it may just be coverage/subprocess issue. -bf
    if _coverage():
        return

    p4_repr = _format_source_code(p4_repr)
    result = difflib.unified_diff(
        p4_orig_lines,
        p4_repr.splitlines(),
        p4_orig.name,
        "new",
    )

    result_lines = list(result)
    # if result_lines:
    #    p4_orig.write_text(p4_repr)
    assert not result_lines


def _format_source_code(source):
    "Format the given source code using `black` formatter."
    return subprocess.check_output(
        ["black", "-"],
        input=source,
        stderr=subprocess.DEVNULL,  # comment out this line to see error msgs!
        encoding="utf-8",
        timeout=20.0,
    )


@pytest.mark.parametrize("p4info_file", P4INFO_TEST_DIR.glob("*.p4info.txt"))
def test_p4info_str(p4info_file):
    "Test output of P4Schema description files."
    p4 = P4Schema(p4info_file)

    p4_orig = Path(p4info_file).with_suffix(".str.txt")
    if p4_orig.exists():
        p4_orig_lines = p4_orig.read_text().splitlines()
    else:
        p4_orig_lines = []

    p4_str = str(p4)
    result = difflib.unified_diff(
        p4_orig_lines,
        p4_str.splitlines(),
        p4_orig.name,
        "new",
    )

    result_lines = list(result)
    # if result_lines:
    #    p4_orig.write_text(p4_str)
    assert not result_lines


def test_p4info_lookup():
    schema = P4Schema(P4INFO_TEST_DIR / "basic.p4.p4info.txt")

    with pytest.raises(
        ValueError,
        match="no P4Register named 'bloom'. Did you mean 'counter_bloom_filter'?",
    ):
        schema.registers["bloom"]


def _make_bitstring(bitwidth) -> p4t.P4BitstringLikeTypeSpec:
    return p4t.P4BitstringLikeTypeSpec(
        bit=p4t.P4BitTypeSpec(
            bitwidth=bitwidth,
        )
    )


def test_p4bitstype():
    "Test P4BitsType."
    bits = P4BitsType(_make_bitstring(8))
    assert bits.bitwidth == 8
    assert not bits.signed and not bits.varbit
    assert bits.type_name == "u8"
    assert pbutil.to_dict(bits.data_type_spec) == {
        "bitstring": {"bit": {"bitwidth": 8}}
    }

    assert bits.encode_bytes(0) == b"\x00"
    assert bits.decode_bytes(b"\x00") == 0

    assert bits.encode_bytes(255) == b"\xFF"
    assert bits.decode_bytes(b"\xFF") == 255

    data = bits.encode_data(0)
    assert pbutil.to_dict(data) == {"bitstring": "AA=="}
    assert bits.decode_data(data) == 0

    data = bits.encode_data(255)
    assert pbutil.to_dict(data) == {"bitstring": "/w=="}
    assert bits.decode_data(data) == 255

    # Test invalid data value.
    with pytest.raises(ValueError, match="invalid value for bitwidth 8"):
        bits.encode_data(65535)


def test_p4bitstype_signed():
    "Test P4BitsType with signed value."
    bits = P4BitsType(
        p4t.P4BitstringLikeTypeSpec(
            int=p4t.P4IntTypeSpec(
                bitwidth=8,
            )
        )
    )
    assert bits.bitwidth == 8
    assert bits.signed and not bits.varbit
    assert bits.type_name == "s8"
    assert pbutil.to_dict(bits.data_type_spec) == {
        "bitstring": {"int": {"bitwidth": 8}}
    }

    assert bits.encode_bytes(-128) == b"\x80"
    assert bits.decode_bytes(b"\x80") == -128

    assert bits.encode_bytes(127) == b"\x7F"
    assert bits.decode_bytes(b"\x7F") == 127

    data = bits.encode_data(-128)
    assert pbutil.to_dict(data) == {"bitstring": "gA=="}
    assert bits.decode_data(data) == -128

    data = bits.encode_data(127)
    assert pbutil.to_dict(data) == {"bitstring": "fw=="}
    assert bits.decode_data(data) == 127

    # Test invalid data value.
    with pytest.raises(ValueError, match="invalid SIGNED value for bitwidth"):
        bits.encode_data(255)


def test_p4bitstype_varbit():
    "Test P4BitsType with varbit value."
    bits = P4BitsType(
        p4t.P4BitstringLikeTypeSpec(
            varbit=p4t.P4VarbitTypeSpec(
                max_bitwidth=8,
            )
        )
    )
    assert bits.bitwidth == 8
    assert not bits.signed and bits.varbit
    assert bits.type_name == "vb8"
    assert pbutil.to_dict(bits.data_type_spec) == {
        "bitstring": {"varbit": {"max_bitwidth": 8}}
    }

    assert bits.encode_bytes(0) == b"\x00"
    assert bits.decode_bytes(b"\x00") == 0

    assert bits.encode_bytes(255) == b"\xFF"
    assert bits.decode_bytes(b"\xFF") == 255

    data = bits.encode_data((0, 8))
    assert pbutil.to_dict(data) == {"varbit": {"bitstring": "AA==", "bitwidth": 8}}
    assert bits.decode_data(data) == (0, 8)

    data = bits.encode_data((255, 8))
    assert pbutil.to_dict(data) == {"varbit": {"bitstring": "/w==", "bitwidth": 8}}
    assert bits.decode_data(data) == (255, 8)

    # Test invalid data value.
    with pytest.raises(ValueError, match="invalid value for bitwidth 8"):
        bits.encode_data((256, 8))

    # Test invalid bitwidth value.
    with pytest.raises(ValueError, match="invalid bitwidth: 9"):
        bits.encode_data((1, 9))

    # Test invalid type.
    with pytest.raises(ValueError, match="expected 2-tuple"):
        bits.encode_data(1)


def test_p4booltype():
    "Test P4BoolType."
    bool_type = P4BoolType(p4t.P4BoolType())
    assert bool_type.type_name == "bool"
    assert pbutil.to_dict(bool_type.data_type_spec) == {"bool": {}}

    data = bool_type.encode_data(True)
    assert pbutil.to_dict(data) == {"bool": True}
    assert bool_type.decode_data(data) is True

    data = bool_type.encode_data(False)
    assert pbutil.to_dict(data) == {"bool": False}
    assert bool_type.decode_data(data) is False


def _make_header_spec(*fields: str) -> p4t.P4HeaderTypeSpec:
    "Define a new P4HeaderTypeSpec."
    return p4t.P4HeaderTypeSpec(
        members=[
            p4t.P4HeaderTypeSpec.Member(name=field, type_spec=_make_bitstring(8))
            for field in fields
        ]
    )


def _make_header_union_spec(*headers: str) -> p4t.P4HeaderUnionTypeSpec:
    "Define a new P4HeaderUnionTypeSpec."
    return p4t.P4HeaderUnionTypeSpec(
        members=[
            p4t.P4HeaderUnionTypeSpec.Member(
                name=name,
                header=p4t.P4NamedType(name=name),
            )
            for name in headers
        ]
    )


def test_p4headertype():
    "Test P4HeaderType."
    header_spec = _make_header_spec("a")
    header = P4HeaderType("HH", header_spec)
    assert header.type_name == "HH"

    # Test valid header.
    data = header.encode_data({"a": 0})
    assert pbutil.to_dict(data) == {
        "header": {
            "bitstrings": ["AA=="],
            "is_valid": True,
        }
    }
    assert header.decode_data(data) == {"a": 0}

    # Test !is_valid header.
    data = header.encode_data({})
    assert pbutil.to_dict(data) == {"header": {}}
    assert header.decode_data(data) == {}

    # Test header with missing field "a".
    with pytest.raises(ValueError, match="P4Header: missing field"):
        header.encode_data({"b": 0})

    # Test header with extra field "b".
    with pytest.raises(ValueError, match="P4Header: extra parameters"):
        header.encode_data({"a": 0, "b": 1})


def test_p4headeruniontype():
    "Test P4HeaderUnionType."
    headerA = _make_header_spec("a")
    headerB = _make_header_spec("b")

    p4types = p4t.P4TypeInfo(headers={"A": headerA, "B": headerB})
    type_info = P4TypeInfo(p4types)

    union_type = P4HeaderUnionType("HU", _make_header_union_spec("A", "B"))
    union_type._finish_init(type_info)
    assert union_type.type_name == "HU"

    data = union_type.encode_union({"A": {"a": 0}})
    assert pbutil.to_dict(data) == {
        "valid_header": {"bitstrings": ["AA=="], "is_valid": True},
        "valid_header_name": "A",
    }
    assert union_type.decode_union(data) == {"A": {"a": 0}}

    data = union_type.encode_data({"A": {"a": 0}})
    assert pbutil.to_dict(data) == {
        "header_union": {
            "valid_header": {"bitstrings": ["AA=="], "is_valid": True},
            "valid_header_name": "A",
        }
    }
    assert union_type.decode_data(data) == {"A": {"a": 0}}

    # Empty union.
    data = union_type.encode_data({})
    assert pbutil.to_dict(data) == {"header_union": {}}
    assert union_type.decode_data(data) == {}

    with pytest.raises(ValueError, match="P4HeaderUnion: wrong header"):
        union_type.encode_data({"C": {"a": 0}})

    with pytest.raises(ValueError, match="P4HeaderUnion: too many headers"):
        union_type.encode_data({"A": {"a": 0}, "B": {"b": 0}})


def test_p4headerstacktype():
    "Test P4HeaderStackType."
    headerA = _make_header_spec("a")
    stack_spec = p4t.P4HeaderStackTypeSpec(
        header=p4t.P4NamedType(name="A"),
        size=2,
    )
    p4types = p4t.P4TypeInfo(headers={"A": headerA})
    type_info = P4TypeInfo(p4types)

    stack_type = P4HeaderStackType(stack_spec, type_info)
    assert stack_type.type_name == "A[2]"

    data = stack_type.encode_data([{"a": 1}, {"a": 2}])
    assert pbutil.to_dict(data) == {
        "header_stack": {
            "entries": [
                {"bitstrings": ["AQ=="], "is_valid": True},
                {"bitstrings": ["Ag=="], "is_valid": True},
            ]
        }
    }
    assert stack_type.decode_data(data) == [{"a": 1}, {"a": 2}]

    with pytest.raises(ValueError, match="P4HeaderStack: expected 2 items"):
        stack_type.encode_data([{"a": 3}])


def test_p4headerunionstacktype():
    "Test P4HeaderUnionStackType."
    headerA = _make_header_spec("a")
    headerB = _make_header_spec("b")
    unionU = _make_header_union_spec("A", "B")

    p4types = p4t.P4TypeInfo(
        headers={"A": headerA, "B": headerB},
        header_unions={"U": unionU},
    )
    type_info = P4TypeInfo(p4types)

    union_stack = p4t.P4HeaderUnionStackTypeSpec(
        header_union=p4t.P4NamedType(name="U"),
        size=2,
    )
    stack = P4HeaderUnionStackType(union_stack, type_info)
    assert stack.type_name == "U[2]"

    data = stack.encode_data([{"A": {"a": 0}}, {"B": {"b": 1}}])
    assert pbutil.to_dict(data) == {
        "header_union_stack": {
            "entries": [
                {
                    "valid_header": {"bitstrings": ["AA=="], "is_valid": True},
                    "valid_header_name": "A",
                },
                {
                    "valid_header": {"bitstrings": ["AQ=="], "is_valid": True},
                    "valid_header_name": "B",
                },
            ]
        }
    }
    assert stack.decode_data(data) == [{"A": {"a": 0}}, {"B": {"b": 1}}]

    with pytest.raises(ValueError, match="P4HeaderUnionStack: expected 2 items"):
        stack.encode_data([{"A": {"a": 0}}])


def test_p4structtype():
    "Test P4StructType."
    bits_t = p4t.P4DataTypeSpec(bitstring=_make_bitstring(8))
    header_t = p4t.P4DataTypeSpec(header=p4t.P4NamedType(name="H"))

    struct_spec = p4t.P4StructTypeSpec(
        members=[
            p4t.P4StructTypeSpec.Member(name="a", type_spec=bits_t),
            p4t.P4StructTypeSpec.Member(name="b", type_spec=header_t),
        ]
    )

    type_info_t = p4t.P4TypeInfo(headers={"H": _make_header_spec("h")})
    type_info = P4TypeInfo(type_info_t)

    struct = P4StructType("S", struct_spec)
    struct._finish_init(type_info)
    assert struct.type_name == "S"

    data = struct.encode_data({"a": 1, "b": {"h": 2}})
    assert pbutil.to_dict(data) == {
        "struct": {
            "members": [
                {"bitstring": "AQ=="},
                {"header": {"bitstrings": ["Ag=="], "is_valid": True}},
            ]
        }
    }
    assert struct.decode_data(data) == {"a": 1, "b": {"h": 2}}

    with pytest.raises(ValueError, match="P4Struct: missing field"):
        struct.encode_data({})

    with pytest.raises(ValueError, match="P4Struct: extra parameters {'z'}"):
        struct.encode_data({"a": 1, "b": {"h": 2}, "z": 10})


def test_p4tupletype():
    "Test P4TupleType."
    bits_t = p4t.P4DataTypeSpec(bitstring=_make_bitstring(8))
    header_t = p4t.P4DataTypeSpec(header=p4t.P4NamedType(name="H"))
    tuple_spec = p4t.P4TupleTypeSpec(members=[bits_t, header_t])

    type_info_t = p4t.P4TypeInfo(headers={"H": _make_header_spec("h")})
    type_info = P4TypeInfo(type_info_t)

    tple = P4TupleType(tuple_spec, type_info)
    assert tple.type_name == "tuple[u8, H]"

    data = tple.encode_data((1, {"h": 2}))
    assert pbutil.to_dict(data) == {
        "tuple": {
            "members": [
                {"bitstring": "AQ=="},
                {"header": {"bitstrings": ["Ag=="], "is_valid": True}},
            ]
        }
    }
    assert tple.decode_data(data) == (1, {"h": 2})

    with pytest.raises(ValueError, match="P4Tuple: expected 2 items"):
        tple.encode_data(())

    with pytest.raises(ValueError, match="P4Tuple: expected 2 items"):
        tple.encode_data((1, {"h": 2}, 3))

    with pytest.raises(ValueError, match="invalid value"):
        tple.encode_data(({"h": 2}, 1))


def test_p4newtype_sdnstring():
    "Test P4NewType."
    newtype_spec = p4t.P4NewTypeSpec(
        translated_type=p4t.P4NewTypeTranslation(
            uri="abc",
            sdn_string=p4t.P4NewTypeTranslation.SdnString(),
        )
    )

    type_info = P4TypeInfo(p4t.P4TypeInfo())

    newtype = P4NewType("some_name", newtype_spec)
    newtype._finish_init(type_info)
    assert newtype.type_name == "some_name"

    data = newtype.encode_data("xyz")
    assert pbutil.to_dict(data) == {"bitstring": "eHl6"}
    assert newtype.decode_data(data) == "xyz"

    data = newtype.encode_data(b"xyz")
    assert pbutil.to_dict(data) == {"bitstring": "eHl6"}
    assert newtype.decode_data(data) == "xyz"

    assert repr(newtype) == "P4NewType(sdn_string, uri='abc', type_name='some_name')"


def test_p4newtype_sdnbitwidth():
    "Test P4NewType."
    newtype_spec = p4t.P4NewTypeSpec(
        translated_type=p4t.P4NewTypeTranslation(
            uri="abc",
            sdn_bitwidth=32,
        )
    )

    type_info = P4TypeInfo(p4t.P4TypeInfo())

    newtype = P4NewType("some_name", newtype_spec)
    newtype._finish_init(type_info)
    assert newtype.type_name == "some_name"

    data = newtype.encode_data(128)
    assert pbutil.to_dict(data) == {"bitstring": "gA=="}
    assert newtype.decode_data(data) == 128

    assert (
        repr(newtype) == "P4NewType(sdn_bitwidth=32, uri='abc', type_name='some_name')"
    )


def test_p4newtype_original_type():
    "Test P4NewType."
    bits_t = p4t.P4DataTypeSpec(bitstring=_make_bitstring(8))
    newtype_spec = p4t.P4NewTypeSpec(original_type=bits_t)

    type_info = P4TypeInfo(p4t.P4TypeInfo())

    newtype = P4NewType("some_name", newtype_spec)
    newtype._finish_init(type_info)
    assert newtype.type_name == "some_name"

    data = newtype.encode_data(128)
    assert pbutil.to_dict(data) == {"bitstring": "gA=="}
    assert newtype.decode_data(data) == 128

    assert (
        repr(newtype) == "P4NewType(original_type=P4BitsType(annotations=[],"
        " bitwidth=8, signed=False, type_name='u8', varbit=False), type_name='some_name')"
    )


def test_p4matchfield_exact():
    "Test P4MatchField with exact match type."
    match_p4 = p4i.MatchField(
        id=1,
        name="f1",
        bitwidth=32,
        match_type=p4i.MatchField.EXACT,
    )
    field = P4MatchField(match_p4)

    field_p4 = field.encode_field("10.0.0.1")
    assert field_p4 is not None
    assert pbutil.to_dict(field_p4) == {
        "field_id": 1,
        "exact": {"value": "CgAAAQ=="},
    }

    assert field.decode_field(field_p4) == 167772161
    assert field.format_field("10.0.0.1") == "0xa000001"

    field._format |= p4values.DecodeFormat.ADDRESS
    assert field.decode_field(field_p4) == IPv4Address("10.0.0.1")
    assert field.format_field("10.0.0.1") == "10.0.0.1"


def test_p4matchfield_lpm():
    "Test P4MatchField with lpm match type."
    match_p4 = p4i.MatchField(
        id=1,
        name="f1",
        bitwidth=32,
        match_type=p4i.MatchField.LPM,
    )
    field = P4MatchField(match_p4)

    field_p4 = field.encode_field("10.0.0.0/8")
    assert field_p4 is not None
    assert pbutil.to_dict(field_p4) == {
        "field_id": 1,
        "lpm": {"prefix_len": 8, "value": "CgAAAA=="},
    }
    assert field.encode_field("0.0.0.0/0") is None

    assert field.decode_field(field_p4) == (167772160, 8)
    assert field.format_field("10.0.0.0/8") == "0xa000000/8"
    assert field.format_field("0.0.0.0/0") == "0x0/0"

    field._format |= p4values.DecodeFormat.ADDRESS
    assert field.decode_field(field_p4) == IPv4Network("10.0.0.0/8")
    assert field.format_field("10.0.0.0/8") == "10.0.0.0/8"
    assert field.format_field("0.0.0.0/0") == "0.0.0.0/0"


def test_p4matchfield_ternary():
    "Test P4MatchField with ternary match type."
    match_p4 = p4i.MatchField(
        id=1,
        name="f1",
        bitwidth=32,
        match_type=p4i.MatchField.TERNARY,
    )
    field = P4MatchField(match_p4)

    field_p4 = field.encode_field("10.0.0.0/255.0.0.0")
    assert field_p4 is not None
    assert pbutil.to_dict(field_p4) == {
        "field_id": 1,
        "ternary": {"mask": "/wAAAA==", "value": "CgAAAA=="},
    }
    assert field.encode_field("0.0.0.0/0.0.0.0") is None

    assert field.decode_field(field_p4) == (167772160, 4278190080)
    assert field.format_field("10.0.0.0/255.0.0.0") == "0xa000000/8"

    field._format |= p4values.DecodeFormat.ADDRESS
    assert field.decode_field(field_p4) == (
        IPv4Address("10.0.0.0"),
        IPv4Address("255.0.0.0"),
    )
    assert field.format_field("10.0.0.0/255.0.0.0") == "10.0.0.0/8"


def test_p4matchfield_range():
    "Test P4MatchField with range match type."
    match_p4 = p4i.MatchField(
        id=1,
        name="f1",
        bitwidth=32,
        match_type=p4i.MatchField.RANGE,
    )
    field = P4MatchField(match_p4)

    field_p4 = field.encode_field((23, 25))
    assert field_p4 is not None
    assert pbutil.to_dict(field_p4) == {
        "field_id": 1,
        "range": {"high": "GQ==", "low": "Fw=="},
    }

    field_p4 = field.encode_field("10.0.0.0 ... 10.0.0.5")
    assert field_p4 is not None

    assert pbutil.to_dict(field_p4) == {
        "field_id": 1,
        "range": {"high": "CgAABQ==", "low": "CgAAAA=="},
    }
    assert field.decode_field(field_p4) == (167772160, 167772165)
    assert field.format_field("10.0.0.0 ... 10.0.0.5") == "0xa000000...0xa000005"

    field._format |= p4values.DecodeFormat.ADDRESS
    assert field.decode_field(field_p4) == (
        IPv4Address("10.0.0.0"),
        IPv4Address("10.0.0.5"),
    )
    assert field.format_field("10.0.0.0 ... 10.0.0.5") == "10.0.0.0...10.0.0.5"


def test_p4matchfield_optional():
    "Test P4MatchField with optional match type."
    match_p4 = p4i.MatchField(
        id=1,
        name="f1",
        bitwidth=32,
        match_type=p4i.MatchField.OPTIONAL,
    )
    field = P4MatchField(match_p4)

    assert field.encode_field(None) is None

    field_p4 = field.encode_field("10.0.0.1")
    assert field_p4 is not None

    assert pbutil.to_dict(field_p4) == {
        "field_id": 1,
        "optional": {"value": "CgAAAQ=="},
    }
    assert field.decode_field(field_p4) == 167772161
    assert field.format_field("10.0.0.1") == "0xa000001"

    field._format |= p4values.DecodeFormat.ADDRESS
    assert field.decode_field(field_p4) == IPv4Address("10.0.0.1")
    assert field.format_field("10.0.0.1") == "10.0.0.1"


def test_parse_type_spec_tuple():
    "Test the `parse_type_spec` function with a tuple."
    bits_t = p4t.P4DataTypeSpec(bitstring=_make_bitstring(8))
    tuple_spec = p4t.P4TupleTypeSpec(members=[bits_t, bits_t])

    type_info = P4TypeInfo(p4t.P4TypeInfo())
    tuple_type = p4t.P4DataTypeSpec(tuple=tuple_spec)

    typ = _parse_type_spec(tuple_type, type_info)
    assert typ.type_name == "tuple[u8, u8]"


def test_p4actionparam():
    "Test P4ActionParam."
    p4param = p4i.Action.Param(id=1, name="xyz", bitwidth=16)
    param = P4ActionParam(p4param)
    # Skipping param._finish_init(...)

    data = param.encode_param(1024)
    assert pbutil.to_dict(data) == {"param_id": 1, "value": "BAA="}
    assert param.decode_param(data) == 1024
    assert param.format_param(1024) == "0x400"


def test_p4schemacache():
    "Test P4SchemaCache."
    p4info = Path(P4INFO_TEST_DIR, "basic.p4.p4info.txt")
    schema = None

    # Without cache: All p4defs should be different objects.
    schemas = [P4Schema(p4info) for _ in range(10)]
    for schema in schemas[1:]:
        assert schema._p4defs is not schemas[0]._p4defs
        assert schema._p4cookie == schemas[0]._p4cookie

    # With cache: All p4defs should be the same object.
    with P4SchemaCache() as cache:
        schemas = [P4Schema(p4info) for _ in range(10)]
        for schema in schemas[1:]:
            assert schema._p4defs is schemas[0]._p4defs
            assert schema._p4cookie == schemas[0]._p4cookie

    # Test weak ref implementation forgets references...
    assert len(cache) == 1
    del schema
    del schemas
    assert len(cache) == 0


def test_p4info_externs():
    "Test externs in P4Schema."
    p4 = P4Schema(Path(P4INFO_TEST_DIR, "externs.p4info.txt"))

    assert len(p4.externs) == 4
    assert [ex.id for ex in p4.externs] == [1, 2, 1, 2]
    assert p4.externs.get(("", "")) is None
    with pytest.raises(ValueError, match="no extern"):
        p4.externs["", ""]

    extern1 = p4.externs[("x", "instance1")]
    assert extern1.id == 1
    assert extern1.name == "instance1"
    assert extern1.extern_type_name == "x"
    assert extern1.extern_type_id == 1

    extern2 = p4.externs.get(("x", "instance2"))
    assert extern2 is not None
    assert extern2.id == 2
    assert extern2.name == "instance2"
    assert extern2.extern_type_name == "x"
    assert extern2.extern_type_id == 1
