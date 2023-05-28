"Test types using P4TypeFactory."

from typing import Any

import pytest

import finsy.p4schema as p4s
from finsy import pbuf
from finsy.proto import p4d
from finsy.test.p4typefactory import P4TypeFactory


def _to_hex(msg: p4d.P4Data) -> str:
    "Return hex encoding of non-deterministic serialization."
    return msg.SerializeToString(deterministic=False).hex()


@pytest.fixture
def type_factory():
    return P4TypeFactory()


def check_roundtrip(
    type_t: p4s._P4Type,
    value: Any,
    expected_hex: str,
    decode_val: Any = None,
):
    "Verify that a type encodes/decodes correctly to/from P4Data."
    msg = type_t.encode_data(value)
    assert _to_hex(msg) == expected_hex

    expected_val = value if decode_val is None else decode_val
    assert type_t.decode_data(msg) == expected_val


def test_bool(type_factory: P4TypeFactory):
    "Test P4BoolType."
    bool_t = type_factory.bool_type()
    assert pbuf.to_dict(bool_t.data_type_spec) == {"bool": {}}

    check_roundtrip(bool_t, True, "1801")
    check_roundtrip(bool_t, False, "1800")
    check_roundtrip(bool_t, 77, "1801", True)
    check_roundtrip(bool_t, None, "", False)  # FIXME: This doesn't seem right.

    with pytest.raises(TypeError, match="cannot be interpreted as an integer"):
        check_roundtrip(bool_t, "x", "")


def test_u32(type_factory: P4TypeFactory):
    "Test bits<32>."
    u32_t = type_factory.bits_type(32)
    assert pbuf.to_dict(u32_t.data_type_spec) == {
        "bitstring": {
            "bit": {"bitwidth": 32},
        }
    }

    check_roundtrip(u32_t, 0, "0a0100")
    check_roundtrip(u32_t, 2**7, "0a0180")
    check_roundtrip(u32_t, 2**8 - 1, "0a01ff")
    check_roundtrip(u32_t, 2**8, "0a020100")
    check_roundtrip(u32_t, 2**16 - 1, "0a02ffff")
    check_roundtrip(u32_t, 2**16, "0a03010000")
    check_roundtrip(u32_t, 2**32 - 128, "0a04ffffff80")
    check_roundtrip(u32_t, 2**32 - 1, "0a04ffffffff")

    with pytest.raises(ValueError, match="invalid value for bitwidth 32"):
        check_roundtrip(u32_t, 2**32, "")

    with pytest.raises(ValueError, match="invalid value for bitwidth 32"):
        check_roundtrip(u32_t, -1, "")


def test_u13(type_factory: P4TypeFactory):
    "Test bits<13>."
    u13_t = type_factory.bits_type(13)
    assert pbuf.to_dict(u13_t.data_type_spec) == {
        "bitstring": {
            "bit": {"bitwidth": 13},
        }
    }

    check_roundtrip(u13_t, 0, "0a0100")
    check_roundtrip(u13_t, 2**7, "0a0180")
    check_roundtrip(u13_t, 2**8 - 1, "0a01ff")
    check_roundtrip(u13_t, 2**8, "0a020100")
    check_roundtrip(u13_t, 2**13 - 1, "0a021fff")

    with pytest.raises(ValueError, match="invalid value for bitwidth 13"):
        check_roundtrip(u13_t, 2**13, "")

    with pytest.raises(ValueError, match="invalid value for bitwidth 13"):
        check_roundtrip(u13_t, -1, "")


def test_u3(type_factory: P4TypeFactory):
    "Test bits<3>."
    u3_t = type_factory.bits_type(3)
    assert pbuf.to_dict(u3_t.data_type_spec) == {
        "bitstring": {
            "bit": {"bitwidth": 3},
        }
    }

    check_roundtrip(u3_t, 0, "0a0100")
    check_roundtrip(u3_t, 2**3 - 1, "0a0107")

    with pytest.raises(ValueError, match="invalid value for bitwidth 3"):
        check_roundtrip(u3_t, 2**3, "")

    with pytest.raises(ValueError, match="invalid value for bitwidth 3"):
        check_roundtrip(u3_t, -1, "")


def test_i32(type_factory: P4TypeFactory):
    "Test int<32>."
    i32_t = type_factory.bits_type(32, signed=True)
    assert pbuf.to_dict(i32_t.data_type_spec) == {
        "bitstring": {
            "int": {"bitwidth": 32},
        }
    }

    # Positive numbers.
    check_roundtrip(i32_t, 0, "0a0100")
    check_roundtrip(i32_t, 2**7, "0a020080")
    check_roundtrip(i32_t, 2**31 - 128, "0a047fffff80")
    check_roundtrip(i32_t, 2**8 - 1, "0a0200ff")
    check_roundtrip(i32_t, 2**8, "0a020100")
    check_roundtrip(i32_t, 2**16 - 1, "0a0300ffff")
    check_roundtrip(i32_t, 2**16, "0a03010000")
    check_roundtrip(i32_t, 2**31 - 1, "0a047fffffff")

    with pytest.raises(ValueError, match="invalid SIGNED value for bitwidth"):
        check_roundtrip(i32_t, 2**31, "")

    with pytest.raises(ValueError, match="invalid SIGNED value for bitwidth"):
        check_roundtrip(i32_t, 2**32 - 1, "")

    # Negative numbers.
    check_roundtrip(i32_t, -1, "0a01ff")
    check_roundtrip(i32_t, -(2**7), "0a0180")
    check_roundtrip(i32_t, -(2**31) + 128, "0a0480000080")
    check_roundtrip(i32_t, -(2**8) + 1, "0a02ff01")
    check_roundtrip(i32_t, -(2**8), "0a02ff00")
    check_roundtrip(i32_t, -(2**16) + 1, "0a03ff0001")
    check_roundtrip(i32_t, -(2**16), "0a03ff0000")
    check_roundtrip(i32_t, -(2**31) + 1, "0a0480000001")
    check_roundtrip(i32_t, -(2**31), "0a0480000000")

    with pytest.raises(ValueError, match="invalid SIGNED value for bitwidth"):
        check_roundtrip(i32_t, -(2**31) - 1, "")

    with pytest.raises(ValueError, match="invalid SIGNED value for bitwidth"):
        check_roundtrip(i32_t, -(2**32) + 1, "")


def test_i13(type_factory: P4TypeFactory):
    "Test int<13>."
    i13_t = type_factory.bits_type(13, signed=True)
    assert pbuf.to_dict(i13_t.data_type_spec) == {
        "bitstring": {
            "int": {"bitwidth": 13},
        }
    }

    # Positive numbers.
    check_roundtrip(i13_t, 0, "0a0100")
    check_roundtrip(i13_t, 2**8 - 1, "0a0200ff")
    check_roundtrip(i13_t, 2**8, "0a020100")
    check_roundtrip(i13_t, 2**11, "0a020800")
    check_roundtrip(i13_t, 2**12 - 1, "0a020fff")

    with pytest.raises(ValueError, match="invalid SIGNED value for bitwidth"):
        check_roundtrip(i13_t, 2**12, "")

    with pytest.raises(ValueError, match="invalid SIGNED value for bitwidth"):
        check_roundtrip(i13_t, 2**13 - 1, "")

    # Negative numbers.
    check_roundtrip(i13_t, -1, "0a01ff")
    check_roundtrip(i13_t, -(2**8) + 1, "0a02ff01")
    check_roundtrip(i13_t, -(2**8), "0a02ff00")
    check_roundtrip(i13_t, -(2**11), "0a02f800")
    check_roundtrip(i13_t, -(2**12), "0a02f000")

    with pytest.raises(ValueError, match="invalid SIGNED value for bitwidth"):
        check_roundtrip(i13_t, -(2**12) - 1, "")

    with pytest.raises(ValueError, match="invalid SIGNED value for bitwidth"):
        check_roundtrip(i13_t, -(2**13) + 1, "")


def test_i3(type_factory: P4TypeFactory):
    "Test int<3>."
    i3_t = type_factory.bits_type(3, signed=True)
    assert pbuf.to_dict(i3_t.data_type_spec) == {
        "bitstring": {
            "int": {"bitwidth": 3},
        }
    }

    # Positive numbers.
    check_roundtrip(i3_t, 0, "0a0100")
    check_roundtrip(i3_t, 2**2 - 1, "0a0103")

    with pytest.raises(ValueError, match="invalid SIGNED value for bitwidth"):
        check_roundtrip(i3_t, 2**2, "0a0104")

    with pytest.raises(ValueError, match="invalid SIGNED value for bitwidth"):
        check_roundtrip(i3_t, 2**3 - 1, "0a0107")

    # Negative numbers.
    check_roundtrip(i3_t, -1, "0a01ff")
    check_roundtrip(i3_t, -(2**2), "0a01fc")

    with pytest.raises(ValueError, match="invalid SIGNED value for bitwidth"):
        check_roundtrip(i3_t, -(2**2) - 1, "")

    with pytest.raises(ValueError, match="invalid SIGNED value for bitwidth"):
        check_roundtrip(i3_t, 2**3 - 1, "")
