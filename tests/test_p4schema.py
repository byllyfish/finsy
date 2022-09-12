import difflib
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from finsy import pbuf
from finsy.p4schema import (
    P4BitsType,
    P4BoolType,
    P4EntityMap,
    P4HeaderStackType,
    P4HeaderType,
    P4HeaderUnionStackType,
    P4HeaderUnionType,
    P4MatchField,
    P4MatchType,
    P4Schema,
    P4StructType,
    P4TupleType,
    P4TypeInfo,
)
from finsy.proto import p4i, p4t

P4INFO_TEST_DIR = Path(__file__).parent / "test_data/p4info"


@dataclass
class _Example:
    "Dummy entity used to testing P4EntityMap."
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
def test_p4info(p4info_file):
    p4 = P4Schema(p4info_file)

    p4_orig = Path(p4info_file).with_suffix(".repr.txt")
    if p4_orig.exists():
        p4_orig_lines = p4_orig.read_text().splitlines()
    else:
        p4_orig_lines = []

    p4_repr = _format_source_code(repr(p4))
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
    )


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

    assert bits.encode_bytes(0) == b"\x00"
    assert bits.decode_bytes(b"\x00") == 0

    assert bits.encode_bytes(255) == b"\xFF"
    assert bits.decode_bytes(b"\xFF") == 255

    data = bits.encode_data(0)
    assert pbuf.to_dict(data) == {"bitstring": "AA=="}
    assert bits.decode_data(data) == 0

    data = bits.encode_data(255)
    assert pbuf.to_dict(data) == {"bitstring": "/w=="}
    assert bits.decode_data(data) == 255

    # Test invalid data value.
    with pytest.raises(ValueError, match="invalid value for bitwidth 8"):
        bits.encode_data(65535)


def test_p4booltype():
    "Test P4BoolType."

    bool_type = P4BoolType(p4t.P4BoolType())

    data = bool_type.encode_data(True)
    assert pbuf.to_dict(data) == {"bool": True}
    assert bool_type.decode_data(data) is True

    data = bool_type.encode_data(False)
    assert pbuf.to_dict(data) == {"bool": False}
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
    header = P4HeaderType(header_spec)

    # Test valid header.
    data = header.encode_data({"a": 0})
    assert pbuf.to_dict(data) == {
        "header": {
            "bitstrings": ["AA=="],
            "is_valid": True,
        }
    }
    assert header.decode_data(data) == {"a": 0}

    # Test !is_valid header.
    data = header.encode_data({})
    assert pbuf.to_dict(data) == {"header": {}}
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

    union_type = P4HeaderUnionType(_make_header_union_spec("A", "B"))
    union_type._finish_init(type_info)

    data = union_type.encode_union({"A": {"a": 0}})
    assert pbuf.to_dict(data) == {
        "valid_header": {"bitstrings": ["AA=="], "is_valid": True},
        "valid_header_name": "A",
    }
    assert union_type.decode_union(data) == {"A": {"a": 0}}

    data = union_type.encode_data({"A": {"a": 0}})
    assert pbuf.to_dict(data) == {
        "header_union": {
            "valid_header": {"bitstrings": ["AA=="], "is_valid": True},
            "valid_header_name": "A",
        }
    }
    assert union_type.decode_data(data) == {"A": {"a": 0}}

    # Empty union.
    data = union_type.encode_data({})
    assert pbuf.to_dict(data) == {"header_union": {}}
    assert union_type.decode_data(data) == {}

    with pytest.raises(ValueError, match="P4HeaderUnion: wrong header"):
        union_type.encode_data({"C": {"a": 0}})

    with pytest.raises(ValueError, match="P4HeaderUnion: too many headers"):
        union_type.encode_data({"A": {"a": 0}, "B": {"b": 0}})


def test_p4headerstacktype():
    "Test P4HeaderStackType."

    headerA = _make_header_spec("a")
    stack_type = p4t.P4HeaderStackTypeSpec(
        header=p4t.P4NamedType(name="A"),
        size=2,
    )
    p4types = p4t.P4TypeInfo(headers={"A": headerA})
    type_info = P4TypeInfo(p4types)

    stack_type = P4HeaderStackType(stack_type, type_info)

    data = stack_type.encode_data([{"a": 1}, {"a": 2}])
    assert pbuf.to_dict(data) == {
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

    data = stack.encode_data([{"A": {"a": 0}}, {"B": {"b": 1}}])
    assert pbuf.to_dict(data) == {
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

    struct = P4StructType(struct_spec)
    struct._finish_init(type_info)

    data = struct.encode_data({"a": 1, "b": {"h": 2}})
    assert pbuf.to_dict(data) == {
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
    struct_spec = p4t.P4TupleTypeSpec(members=[bits_t, header_t])

    type_info_t = p4t.P4TypeInfo(headers={"H": _make_header_spec("h")})
    type_info = P4TypeInfo(type_info_t)

    tple = P4TupleType(struct_spec, type_info)

    data = tple.encode_data((1, {"h": 2}))
    assert pbuf.to_dict(data) == {
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

    assert pbuf.to_dict(field_p4) == {
        "field_id": 1,
        "lpm": {"prefix_len": 8, "value": "CgAAAA=="},
    }
    assert field.decode_field(field_p4) == (167772160, 8)

    assert field.encode_field("0.0.0.0/0") is None


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

    assert pbuf.to_dict(field_p4) == {
        "field_id": 1,
        "ternary": {"mask": "/wAAAA==", "value": "CgAAAA=="},
    }
    assert field.decode_field(field_p4) == (167772160, 4278190080)

    assert field.encode_field("0.0.0.0/0.0.0.0") is None
