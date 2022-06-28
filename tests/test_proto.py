import pytest
from finsy.proto import U128

UINT128_VALUES = {
    0: (0, 0),
    1: (0, 1),
    2**64: (1, 0),
    2**127: (9223372036854775808, 0),
    2**128 - 1: (18446744073709551615, 18446744073709551615),
}


def test_uint128():
    "Test the Uint128 conversion function."

    for value, expected in UINT128_VALUES.items():
        result = U128.encode(value)
        assert (result.high, result.low) == expected

    UINT128_INVALID = [2**128, -1, 1.0, 1e10, 1 + 2j]

    for value in UINT128_INVALID:
        with pytest.raises(ValueError):
            U128.encode(value)


def test_uint128_to_int():
    "Test the Uint128 backward conversion function `int`."

    for value in UINT128_VALUES.keys():
        result = U128.encode(value)
        assert U128.decode(result) == value
