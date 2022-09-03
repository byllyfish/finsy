"P4 Value conversion functions."

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

import enum
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from typing import SupportsInt

from macaddress import MAC as MACAddress


class DecodeHint(enum.Enum):
    "Indicate how to decode values."

    DEFAULT = enum.auto()
    ADDRESS = enum.auto()


_ExactValue = SupportsInt | str | bytes
_ExactReturn = int | IPv4Address | IPv6Address | MACAddress

_LPMValue = str | IPv4Network | IPv6Network | tuple[_ExactValue, int]
_LPMReturn = tuple[_ExactReturn, int]

_TernaryValue = (
    SupportsInt | str | IPv4Network | IPv6Network | tuple[_ExactValue, _ExactValue]
)
_TernaryReturn = tuple[_ExactReturn, _ExactReturn] | _ExactReturn

_RangeValue = str | tuple[_ExactValue, _ExactValue]
_RangeReturn = tuple[_ExactReturn, _ExactReturn]

P4ParamValue = _ExactValue


def p4r_minimum_string_size(bitwidth: int) -> int:
    "P4Runtime `minimum_string_size` function (P4R-Spec section 8.4)"

    if bitwidth <= 0:
        raise ValueError(f"invalid bitwidth: {bitwidth}")
    return (bitwidth + 7) // 8


def p4r_truncate(value: bytes, signed: bool = False) -> bytes:
    "Truncate a bytes value to the specified bitwidth."
    assert not signed, "TODO: signed not yet supported"

    return value.lstrip(b"\x00") or b"\x00"


def _parse_str(value: str, bitwidth: int) -> int:
    "Convert string value to an integer."
    value = value.strip()

    if bitwidth == 32 and "." in value:
        return int(IPv4Address(value))

    if bitwidth == 128 and ":" in value:
        return int(IPv6Address(value))

    if bitwidth == 48 and ("-" in value[1:] or ":" in value):
        return int(MACAddress(value))

    try:
        return int(value, base=0)
    except ValueError:
        raise ValueError(f"invalid value for bitwidth {bitwidth}: {value!r}") from None


def encode_exact(value: _ExactValue, bitwidth: int) -> bytes:
    "Encode an exact field value into a byte encoding."
    assert value is not None

    match value:
        case bytes():
            return p4r_truncate(value)
        case str():
            ival = _parse_str(value, bitwidth)
        case float():
            if not value.is_integer():
                raise ValueError(f"fractional float value: {value!r}")
            ival = int(value)
        case _:
            try:
                ival = int(value)
            except TypeError:
                raise ValueError(f"invalid value type: {value!r}") from None

    if ival >= (1 << bitwidth):
        raise OverflowError(f"invalid value for bitwidth {bitwidth}: {value!r}")

    size = p4r_minimum_string_size(bitwidth)
    return p4r_truncate(ival.to_bytes(size, "big"))


def decode_exact(
    data: bytes,
    bitwidth: int,
    hint: DecodeHint = DecodeHint.DEFAULT,
) -> _ExactReturn:
    """Decode a P4R value into an integer or address."""
    if not data:
        raise ValueError("empty data")

    ival = int.from_bytes(data, "big")
    if ival >= (1 << bitwidth):
        raise OverflowError(f"invalid value for bitwidth {bitwidth}: {data!r}")

    match hint:
        case DecodeHint.DEFAULT:
            return ival
        case DecodeHint.ADDRESS if bitwidth == 128:
            return IPv6Address(ival)
        case DecodeHint.ADDRESS if bitwidth == 48:
            return MACAddress(ival)
        case DecodeHint.ADDRESS if bitwidth == 32:
            return IPv4Address(ival)
        case DecodeHint.ADDRESS:
            return ival

    raise ValueError(f"invalid hint: {hint!r}")


def encode_lpm(value: _LPMValue, bitwidth: int) -> tuple[bytes, int]:
    "Encode a string value into a P4R LPM value."
    assert value is not None

    if isinstance(value, (IPv4Network, IPv6Network)):
        if bitwidth != value.max_prefixlen:
            raise ValueError(f"invalid value for bitwidth {bitwidth}: {value!r}")
        data = encode_exact(value.network_address, bitwidth)
        return data, value.prefixlen

    if isinstance(value, int):
        vals = [value]
    elif isinstance(value, str):
        vals = value.split("/", 1)
    elif isinstance(value, tuple):  # pyright: ignore [reportUnnecessaryIsInstance]
        if len(value) != 2:
            raise ValueError(f"invalid tuple value: {value!r}")
        vals = value
    else:
        raise ValueError(f"unexpected type: {value!r}")

    data = encode_exact(vals[0], bitwidth)
    if len(vals) == 2:
        prefix = int(vals[1])
    else:
        prefix = bitwidth

    if prefix > bitwidth or prefix < 0:
        raise ValueError(f"invalid prefix for bitwidth {bitwidth}: {value!r}")

    return data, prefix


def decode_lpm(
    data: bytes,
    prefix_len: int,
    bitwidth: int,
    hint: DecodeHint = DecodeHint.DEFAULT,
) -> _LPMReturn:
    "Decode a P4R Value into an integer or address."

    return (decode_exact(data, bitwidth, hint), prefix_len)


def encode_ternary(value: _TernaryValue, bitwidth: int) -> tuple[bytes, bytes]:
    "Encode a value into a P4R ternary value."
    assert value is not None

    if isinstance(value, (IPv4Network, IPv6Network)):
        val, mask = int(value.network_address), int(value.netmask)
    else:
        match value:
            case int(val):
                mask = _all_ones(bitwidth)
            case str(val):
                val, mask = val.split("/", 1)
            case (val, mask):
                pass
            case other:
                raise ValueError(f"unexpected value: {other!r}")

    return (encode_exact(val, bitwidth), encode_exact(mask, bitwidth))


def decode_ternary(
    data: bytes,
    mask: bytes,
    bitwidth: int,
    hint: DecodeHint = DecodeHint.DEFAULT,
) -> _TernaryReturn:
    "Decode a P4R Ternary value."

    result = (decode_exact(data, bitwidth, hint), decode_exact(mask, bitwidth, hint))
    if result[1] == _all_ones(bitwidth):
        return result[0]
    return result


def encode_range(value: _RangeValue, bitwidth: int) -> tuple[bytes, bytes]:
    "Encode a P4R Range value."
    assert value is not None

    match value:
        case str(val):
            low, high = val.split("...", 1)
        case (low, high):
            pass
        case other:
            raise ValueError(f"unexpected value: {other!r}")

    return (encode_exact(low, bitwidth), encode_exact(high, bitwidth))


def decode_range(
    low: bytes,
    high: bytes,
    bitwidth: int,
    hint: DecodeHint = DecodeHint.DEFAULT,
) -> _RangeReturn:
    "Decode a P4R Range value."

    return (decode_exact(low, bitwidth, hint), decode_exact(high, bitwidth, hint))


def _all_ones(bitwidth: int) -> int:
    "Return integer value with `bitwidth` 1's."
    return (1 << bitwidth) - 1
