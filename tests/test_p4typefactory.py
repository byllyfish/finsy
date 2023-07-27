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
    type_t: p4s.P4Type,
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


def test_vb32(type_factory: P4TypeFactory):
    "Test varbit<32>."
    vb32_t = type_factory.bits_type(32, varbit=True)
    assert pbuf.to_dict(vb32_t.data_type_spec) == {
        "bitstring": {
            "varbit": {"max_bitwidth": 32},
        }
    }

    check_roundtrip(vb32_t, (0, 16), "12050a01001010")
    check_roundtrip(vb32_t, (2**7, 16), "12050a01801010")
    check_roundtrip(vb32_t, (2**8 - 1, 16), "12050a01ff1010")
    check_roundtrip(vb32_t, (2**8, 16), "12060a0201001010")
    check_roundtrip(vb32_t, (2**16 - 1, 16), "12060a02ffff1010")

    check_roundtrip(vb32_t, (2**16, 32), "12070a030100001020")
    check_roundtrip(vb32_t, (2**32 - 128, 32), "12080a04ffffff801020")
    check_roundtrip(vb32_t, (2**32 - 1, 32), "12080a04ffffffff1020")

    with pytest.raises(ValueError, match="invalid value for bitwidth 16"):
        check_roundtrip(vb32_t, (2**32, 16), "")

    with pytest.raises(ValueError, match="invalid value for bitwidth 32"):
        check_roundtrip(vb32_t, (2**32, 32), "")

    with pytest.raises(ValueError, match="invalid value for bitwidth 32"):
        check_roundtrip(vb32_t, (-1, 32), "")

    with pytest.raises(ValueError, match="invalid bitwidth"):
        check_roundtrip(vb32_t, (0, 33), "12050a01001010")


def test_vb13(type_factory: P4TypeFactory):
    "Test varbit<13>."
    vb13_t = type_factory.bits_type(13, varbit=True)
    assert pbuf.to_dict(vb13_t.data_type_spec) == {
        "bitstring": {
            "varbit": {"max_bitwidth": 13},
        }
    }

    check_roundtrip(vb13_t, (0, 11), "12050a0100100b")
    check_roundtrip(vb13_t, (2**7, 11), "12050a0180100b")
    check_roundtrip(vb13_t, (2**8 - 1, 11), "12050a01ff100b")
    check_roundtrip(vb13_t, (2**8, 11), "12060a020100100b")
    check_roundtrip(vb13_t, (2**11 - 1, 11), "12060a0207ff100b")
    check_roundtrip(vb13_t, (2**13 - 1, 13), "12060a021fff100d")

    with pytest.raises(ValueError, match="invalid value for bitwidth 13"):
        check_roundtrip(vb13_t, (2**13, 13), "")

    with pytest.raises(ValueError, match="invalid value for bitwidth 13"):
        check_roundtrip(vb13_t, (-1, 13), "")

    with pytest.raises(ValueError, match="invalid bitwidth"):
        check_roundtrip(vb13_t, (0, 14), "12050a01001010")


def test_vb3(type_factory: P4TypeFactory):
    "Test varbit<3>."
    vb3_t = type_factory.bits_type(3, varbit=True)
    assert pbuf.to_dict(vb3_t.data_type_spec) == {
        "bitstring": {
            "varbit": {"max_bitwidth": 3},
        }
    }

    check_roundtrip(vb3_t, (0, 2), "12050a01001002")
    check_roundtrip(vb3_t, (3, 2), "12050a01031002")
    check_roundtrip(vb3_t, (2**3 - 1, 3), "12050a01071003")

    with pytest.raises(ValueError, match="invalid value for bitwidth 3"):
        check_roundtrip(vb3_t, (2**3, 3), "")

    with pytest.raises(ValueError, match="invalid value for bitwidth 3"):
        check_roundtrip(vb3_t, (-1, 3), "")

    with pytest.raises(ValueError, match="invalid bitwidth"):
        check_roundtrip(vb3_t, (0, 4), "12050a01001010")


def test_tuple_type(type_factory: P4TypeFactory):
    "Test tuple<bits<4>, bits<8>>"
    u4_t = type_factory.bits_type(4)
    u8_t = type_factory.bits_type(8)
    tup = type_factory.tuple_type(u4_t, u8_t)

    assert pbuf.to_dict(tup.data_type_spec) == {
        "tuple": {
            "members": [
                {"bitstring": {"bit": {"bitwidth": 4}}},
                {"bitstring": {"bit": {"bitwidth": 8}}},
            ]
        }
    }

    check_roundtrip(tup, (0, 0), "220a0a030a01000a030a0100")
    check_roundtrip(tup, (10, 100), "220a0a030a010a0a030a0164")

    with pytest.raises(ValueError, match="expected 2 items"):
        check_roundtrip(tup, (0,), "")

    with pytest.raises(ValueError, match="expected 2 items"):
        check_roundtrip(tup, (0, 0, 0), "")

    with pytest.raises(ValueError, match="invalid value for bitwidth 4"):
        check_roundtrip(tup, (100, 0), "")


def test_struct_type(type_factory: P4TypeFactory):
    "Test struct<a=bits<4>, b=bits<8>>"
    u4_t = type_factory.bits_type(4)
    u8_t = type_factory.bits_type(8)
    struct = type_factory.struct_type("s", a=u4_t, b=u8_t)

    assert pbuf.to_dict(struct.data_type_spec) == {"struct": {"name": "s"}}

    check_roundtrip(struct, {"a": 0, "b": 0}, "2a0a0a030a01000a030a0100")
    check_roundtrip(struct, {"a": 10, "b": 100}, "2a0a0a030a010a0a030a0164")

    with pytest.raises(ValueError, match="missing field 'b'"):
        check_roundtrip(struct, {"a": 0}, "")

    with pytest.raises(ValueError, match="extra parameters {'c'}"):
        check_roundtrip(struct, {"a": 0, "b": 0, "c": 0}, "")

    with pytest.raises(ValueError, match="invalid value for bitwidth 4"):
        check_roundtrip(struct, {"a": 100, "b": 0}, "")


def test_tuple_of_structs_type(type_factory: P4TypeFactory):
    "Test both tuple and struct types together."
    u4_t = type_factory.bits_type(4)
    u8_t = type_factory.bits_type(8)
    struct = type_factory.struct_type("s", a=u4_t, b=u8_t)
    tup = type_factory.tuple_type(struct, struct)

    assert pbuf.to_dict(tup.data_type_spec) == {
        "tuple": {"members": [{"struct": {"name": "s"}}, {"struct": {"name": "s"}}]}
    }

    value = ({"a": 0, "b": 0}, {"a": 10, "b": 100})
    check_roundtrip(
        tup, value, "221c0a0c2a0a0a030a01000a030a01000a0c2a0a0a030a010a0a030a0164"
    )
