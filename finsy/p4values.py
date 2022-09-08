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


class DecodeFormat(enum.Flag):
    "Indicate how to decode values."

    STRING = enum.auto()
    ADDRESS = enum.auto()
    DEFAULT = 0


_ExactValue = SupportsInt | str
_ExactReturn = int | str | IPv4Address | IPv6Address | MACAddress

_LPMValue = int | str | IPv4Network | IPv6Network | tuple[_ExactValue, int]
_LPMReturn = str | IPv4Network | IPv6Network | tuple[int | MACAddress, int]

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


def _parse_exact_str(value: str, bitwidth: int) -> int:
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


def _decode_addr(value: int, bitwidth: int, format: DecodeFormat):
    "Decode an integer according to the bitwidth and desired output format."
    assert format & DecodeFormat.ADDRESS

    match bitwidth:
        case 128:
            addr = IPv6Address(value)
        case 48:
            addr = MACAddress(value)
        case 32:
            addr = IPv4Address(value)
        case _:
            # Return original integer.
            if format & DecodeFormat.STRING:
                return hex(value)
            return value

    if format & DecodeFormat.STRING:
        return str(addr)

    return addr


# Exact Values
# ~~~~~~~~~~~~
#
# Supported input values for `encode_exact`:
#
# - int
# - str
#   o decimal integer
#   o hexadecimal integer (prefixed with `0x`)
#   o IPv4 string (bitwidth=32 only)
#   o IPv6 string (bitwidth=128 only)
#   o MAC string  (bitwidth=48 only)
# - IPv4Address (bitwidth=32 only)
# - IPv6Address (bitwidth=128 only)
# - MACAddress (bitwidth=48 only)
#
# Canonical output values from `decode_exact`:
#
# - DEFAULT: int
# - STRING: hexadecimal integer prefixed with `0x`
# - ADDRESS:
#   o IPv4Address (bitwidth=32)
#   o IPv6Address (bitwidth=128)
#   o MACAddress (bitwidth=48)
#   o int (all other bitwidths)
# - ADDRESS, STRING:
#   o IPv4 string (bitwidth=32)
#   o IPv6 string (bitwidth=128)
#   o MAC string (bitwidth=48)
#   o hexadecimal integer (all other bitwidths)


def encode_exact(value: _ExactValue, bitwidth: int) -> bytes:
    "Encode an exact field value into a byte encoding."
    assert value is not None

    match value:
        case int():
            ival = value
        case str():
            ival = _parse_exact_str(value, bitwidth)
        case IPv4Address() if bitwidth == 32:
            ival = int(value)
        case IPv6Address() if bitwidth == 128:
            ival = int(value)
        case MACAddress() if bitwidth == 48:
            ival = int(value)
        case _:
            raise ValueError(f"invalid value for bitwidth {bitwidth}: {value!r}")

    if ival >= (1 << bitwidth) or ival < 0:
        raise ValueError(f"invalid value for bitwidth {bitwidth}: {value!r}")

    size = p4r_minimum_string_size(bitwidth)
    return p4r_truncate(ival.to_bytes(size, "big"))


def decode_exact(
    data: bytes,
    bitwidth: int,
    format: DecodeFormat = DecodeFormat.DEFAULT,
) -> _ExactReturn:
    """Decode a P4R value into an integer or address."""
    if not data:
        raise ValueError("empty data")

    ival = int.from_bytes(data, "big")
    if ival >= (1 << bitwidth):
        raise ValueError(f"invalid value for bitwidth {bitwidth}: {data!r}")

    if format & DecodeFormat.ADDRESS:
        return _decode_addr(ival, bitwidth, format)

    if format & DecodeFormat.STRING:
        return hex(ival)

    return ival


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
    format: DecodeFormat = DecodeFormat.DEFAULT,
) -> _LPMReturn:
    "Decode a P4R Value into an integer or address."

    value = decode_exact(data, bitwidth, format)

    match value:
        case IPv4Address():
            return IPv4Network((value, prefix_len))
        case IPv6Address():
            return IPv6Network((value, prefix_len))
        case str():
            return f"{value}/{prefix_len}"
        case _:
            return (value, prefix_len)


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
    hint: DecodeFormat = DecodeFormat.DEFAULT,
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
    hint: DecodeFormat = DecodeFormat.DEFAULT,
) -> _RangeReturn:
    "Decode a P4R Range value."

    return (decode_exact(low, bitwidth, hint), decode_exact(high, bitwidth, hint))


def _all_ones(bitwidth: int) -> int:
    "Return integer value with `bitwidth` 1's."
    return (1 << bitwidth) - 1
