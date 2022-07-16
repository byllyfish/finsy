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
    P4HeaderType,
    P4MatchType,
    P4Schema,
)
from finsy.proto import p4t

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
        stderr=subprocess.DEVNULL,
        encoding="utf-8",
    )


def test_p4info_lookup():
    schema = P4Schema(P4INFO_TEST_DIR / "basic.p4.p4info.txt")

    with pytest.raises(
        ValueError,
        match="no P4Register named 'bloom'. Did you mean 'counter_bloom_filter'?",
    ):
        schema.registers["bloom"]


def test_p4bitstype():
    "Test P4BitsType."

    bit_like = p4t.P4BitstringLikeTypeSpec(
        bit=p4t.P4BitTypeSpec(
            bitwidth=8,
        )
    )

    bits = P4BitsType(bit_like)
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
    with pytest.raises(OverflowError, match="invalid value for bitwidth 8"):
        bits.encode_data(65535)


def test_p4booltype():
    "Test P4BoolType."

    bool_type = P4BoolType(p4t.P4BoolType())

    data = bool_type.encode_data(True)
    assert pbuf.to_dict(data) == {"bool": True}
    assert bool_type.decode_data(data) == True

    data = bool_type.encode_data(False)
    assert pbuf.to_dict(data) == {"bool": False}
    assert bool_type.decode_data(data) == False


def test_p4headertype():
    "Test P4HeaderType."

    bits_spec = p4t.P4BitstringLikeTypeSpec(
        bit=p4t.P4BitTypeSpec(
            bitwidth=8,
        )
    )

    header_spec = p4t.P4HeaderTypeSpec(
        members=[
            p4t.P4HeaderTypeSpec.Member(
                name="a",
                type_spec=bits_spec,
            ),
        ]
    )

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

    # Test header with missing field name.
    with pytest.raises(KeyError, match="a"):  # FIXME: better error message
        header.encode_data({"b": 0})

    # Test header with extra field "b".
    data = header.encode_data({"a": 0, "b": 1})  # FIXME: should error!
    assert pbuf.to_dict(data) == {"header": {"bitstrings": ["AA=="], "is_valid": True}}
