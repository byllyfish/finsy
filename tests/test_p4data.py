from pathlib import Path

import pytest

import finsy.p4schema as P4
from finsy import pbuf
from finsy.p4schema import P4Schema

P4INFO_TEST_DIR = Path(__file__).parent / "test_data/p4info"
SCHEMA = P4Schema(P4INFO_TEST_DIR / "type_info.p4info.txt")


def test_encode_header1():
    header = SCHEMA.type_info.headers["A"]

    data = header.encode_data({"a": 1, "b": 2, "c": 3})

    bin = data.SerializeToString()
    assert bin.hex() == "320b0801120101120102120103"

    assert pbuf.to_dict(data) == {
        "header": {"bitstrings": ["AQ==", "Ag==", "Aw=="], "is_valid": True}
    }
    assert header.decode_data(data) == {"a": 1, "b": 2, "c": 3}

    # Test invalid header..
    data = header.encode_data({})
    assert pbuf.to_dict(data) == {"header": {}}
    assert header.decode_data(data) == {}


def test_encode_struct1():
    struct1 = SCHEMA.type_info.structs["S1"]

    data = struct1.encode_data({"a": 1, "b": 2, "c": 3})
    assert pbuf.to_dict(data) == {
        "struct": {
            "members": [
                {"bitstring": "AQ=="},
                {"bitstring": "Ag=="},
                {"bitstring": "Aw=="},
            ]
        }
    }
    assert struct1.decode_data(data) == {"a": 1, "b": 2, "c": 3}


def test_encode_struct2():
    struct2 = SCHEMA.type_info.structs["S2"]

    data = struct2.encode_data({"a": {"a": 1, "b": 2, "c": 3}, "b": 2})
    assert pbuf.to_dict(data) == {
        "struct": {
            "members": [
                {
                    "struct": {
                        "members": [
                            {"bitstring": "AQ=="},
                            {"bitstring": "Ag=="},
                            {"bitstring": "Aw=="},
                        ]
                    }
                },
                {"bitstring": "Ag=="},
            ]
        }
    }
    assert struct2.decode_data(data) == {"a": {"a": 1, "b": 2, "c": 3}, "b": 2}


def test_encode_struct_malformed():
    struct1 = SCHEMA.type_info.structs["S1"]

    with pytest.raises(ValueError, match="P4Struct: missing field 'c'"):
        struct1.encode_data({"a": 1, "b": 2, "z": 3})


def test_p4data_unsigned_bitstype():
    "Test encoding/decoding a P4Data unsigned bitstype."
    spec = P4.p4t.P4BitstringLikeTypeSpec(bit=P4.p4t.P4BitTypeSpec(bitwidth=16))
    u16 = P4.P4BitsType(spec)

    # Test encode_data().
    data = u16.encode_data(64)
    assert data.SerializeToString().hex() == "0a0140"
    assert u16.decode_data(data) == 64

    # Test encode_bytes().
    assert u16.encode_bytes(64).hex() == "40"
    assert u16.decode_bytes(bytes.fromhex("40")) == 64

    # Test encode_data with too big value.
    with pytest.raises(ValueError, match="invalid value for bitwidth 16"):
        u16.encode_data(2**16 + 1)

    # Test encode_bytes with too big value.
    with pytest.raises(ValueError, match="invalid value for bitwidth 16"):
        u16.encode_bytes(2**16 + 1)

    # Test encode_data with negative value.
    with pytest.raises(ValueError, match="invalid value for bitwidth 16"):
        u16.encode_data(-1)
