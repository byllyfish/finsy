from pathlib import Path

import pytest
from finsy import pbuf
from finsy.p4schema import P4Schema

P4INFO_TEST_DIR = Path(__file__).parent / "test_data/p4info"
SCHEMA = P4Schema(P4INFO_TEST_DIR / "type_info.p4info.txt")


def test_encode_header1():
    header = SCHEMA.type_info.headers["A"]

    data = header.encode_data({"a": 1, "b": 2, "c": 3})
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

    with pytest.raises(KeyError, match="c"):
        struct1.encode_data({"a": 1, "b": 2, "z": 3})
