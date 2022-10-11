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
from typing import Any, SupportsInt

from macaddress import MAC as MACAddress


class DecodeFormat(enum.Flag):
    "Indicate how to decode values."

    STRING = enum.auto()
    ADDRESS = enum.auto()
    DEFAULT = 0


def p4r_minimum_string_size(bitwidth: int) -> int:
    "P4Runtime `minimum_string_size` function (P4R-Spec section 8.4)"

    if bitwidth <= 0:
        raise ValueError(f"invalid bitwidth: {bitwidth}")
    return (bitwidth + 7) // 8


def p4r_truncate(value: bytes, signed: bool = False) -> bytes:
    "Truncate a bytes value to the specified bitwidth."
    assert not signed, "TODO: signed not yet supported"

    return value.lstrip(b"\x00") or b"\x00"


def all_ones(bitwidth: int) -> int:
    "Return integer value with `bitwidth` 1's."

    return (1 << bitwidth) - 1


def mask_to_prefix(value: int, bitwidth: int) -> int:
    "Convert mask bits to prefix count. Return -1 if mask is discontiguous."

    mask = ~value & all_ones(bitwidth)  # complement the bits
    if (mask & (mask + 1)) != 0:
        return -1  # discontiguous
    return bitwidth - mask.bit_length()


def _InvalidErr(kind: str, bitwidth: int, value: Any) -> ValueError:
    "Construct formatted ValueError message."

    # Replace "exact" with empty string. Otherwise, prepend a space.
    if kind == "exact":
        kind = ""
    else:
        kind = f" {kind.upper()}"
    return ValueError(f"invalid{kind} value for bitwidth {bitwidth}: {value!r}")


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
        raise _InvalidErr("exact", bitwidth, value)


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
#   o SdnString (bitwidth=0)
# - IPv4Address (bitwidth=32 only)
# - IPv6Address (bitwidth=128 only)
# - MACAddress (bitwidth=48 only)
#
# (To pass `bytes``, first convert to an int using `int.from_bytes`.)
#
# Canonical output values from `decode_exact`:
#
# - DEFAULT:
#   o int
# - STRING:
#   o hexadecimal integer prefixed with `0x`
#   o SdnString (bitwidth=0)
# - ADDRESS:
#   o IPv4Address (bitwidth=32)
#   o IPv6Address (bitwidth=128)
#   o MACAddress (bitwidth=48)
#   o see DEFAULT
# - ADDRESS, STRING:
#   o IPv4 string (bitwidth=32)
#   o IPv6 string (bitwidth=128)
#   o MAC string (bitwidth=48)
#   o hexadecimal integer (all other bitwidths)

_ExactValue = int | str | IPv4Address | IPv6Address | MACAddress
_ExactReturn = int | str | IPv4Address | IPv6Address | MACAddress

P4ParamValue = _ExactValue


def encode_exact(value: _ExactValue, bitwidth: int, mask: int = ~0) -> bytes:
    """Encode an exact field value into a byte encoding.

    If `bitwidth` is 0, value is an `SdnString`.
    """
    assert value is not None

    if bitwidth == 0:
        # If bitwidth is 0, value is interpreted as `SdnString`.
        if not isinstance(value, str):
            raise ValueError(f"invalid value for SdnString: {value!r}")
        return value.encode()

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
            raise _InvalidErr("exact", bitwidth, value)

    if ival >= (1 << bitwidth) or ival < 0:
        raise _InvalidErr("exact", bitwidth, value)

    size = p4r_minimum_string_size(bitwidth)
    if mask != ~0:
        ival &= mask
    return p4r_truncate(ival.to_bytes(size, "big"))


def decode_exact(
    data: bytes,
    bitwidth: int,
    format: DecodeFormat = DecodeFormat.DEFAULT,
) -> _ExactReturn:
    """Decode a P4R value into an integer or address."""

    if bitwidth == 0:
        # If bitwidth is 0, data is interpreted as `SdnString`.
        return data.decode()

    if not data:
        raise _InvalidErr("exact", bitwidth, data)

    ival = int.from_bytes(data, "big")
    if ival >= (1 << bitwidth):
        raise _InvalidErr("exact", bitwidth, data)

    if format & DecodeFormat.ADDRESS:
        return _decode_addr(ival, bitwidth, format)

    if format & DecodeFormat.STRING:
        return hex(ival)

    return ival


def format_exact(value: _ExactValue, bitwidth: int, format: DecodeFormat) -> str:
    "Format a value as a string."

    data = encode_exact(value, bitwidth)
    result = decode_exact(data, bitwidth, format | DecodeFormat.STRING)
    assert isinstance(result, str)
    return result


# LPM Values
# ~~~~~~~~~~
#
# Supported input values for `encode_lpm`:
#
# - int
# - str
#   o decimal integer
#   o hexadecimal integer (prefixed with `0x`)
#   o IPv4 string (bitwidth=32 only)
#   o IPv6 string (bitwidth=128 only)
#   o MAC string  (bitwidth=48 only)
#   o "value/prefix" where value is any of the above
# - IPv4Address (bitwidth=32 only)
# - IPv6Address (bitwidth=128 only)
# - MACAddress (bitwidth=48 only)
# - IPv4Network (bitwidth=32 only)
# - IPv6Network (bitwidth=128 only)
# - tuple[value, prefix]
#   o tuple[int, int]
#   o tuple[str, int]
#   o tuple[IPv4Address, int] (bitwidth=32 only)
#   o tuple[IPv6Address, int] (bitwidth=128 only)
#   o tuple[MACAddress, int]  (bitwidth=48 only)
#
# Supported output values for `decode_lpm`:
#
# - DEFAULT:
#   o tuple[int, int]
# - STRING:
#   o "value/prefix" with value in hexadecimal
# - ADDRESS:
#   o IPv4Network (bitwidth=32)
#   o IPv6Network (bitwidth=128)
#   o tuple[MACAddress, int] (bitwidth=48)
#   o See DEFAULT output.
# - ADDRESS, STRING
#   o "IPV4/prefix" (bitwidth=32)
#   o "IPV6/prefix" (bitwidth=128)
#   o "MAC/prefix"  (bitwidth=48)
#   o See STRING output.

_LPMValue = (
    int
    | str
    | IPv4Network
    | IPv6Network
    | IPv4Address
    | IPv6Address
    | MACAddress
    | tuple[_ExactValue, int]
)
_LPMReturn = str | IPv4Network | IPv6Network | tuple[int | MACAddress, int]


def _parse_lpm_prefix(value: str, bitwidth: int) -> int:
    "Parse LPM prefix."

    if bitwidth == 32 and "." in value:
        return mask_to_prefix(int(IPv4Address(value)), 32)
    if bitwidth == 128 and ":" in value:
        return mask_to_prefix(int(IPv6Address(value)), 128)
    if bitwidth == 48 and ("-" in value[1:] or ":" in value):
        return mask_to_prefix(int(MACAddress(value)), 48)
    return int(value)


def _parse_lpm_str(value: str, bitwidth: int) -> tuple[bytes, int]:
    "Parse value in slash notation."

    if "/" not in value:
        return (encode_exact(value, bitwidth), bitwidth)

    vals = value.split("/", 1)
    prefix = _parse_lpm_prefix(vals[1], bitwidth)

    if prefix > bitwidth or prefix < 0:
        raise _InvalidErr("lpm", bitwidth, value)

    mask = ~all_ones(bitwidth - prefix)
    return (encode_exact(vals[0], bitwidth, mask), prefix)


def encode_lpm(value: _LPMValue, bitwidth: int) -> tuple[bytes, int]:
    "Encode a value into a P4R LPM value."
    assert value is not None

    if bitwidth == 0:
        raise _InvalidErr("lpm", bitwidth, value)

    match value:
        case int():
            return (encode_exact(value, bitwidth), bitwidth)
        case str():
            return _parse_lpm_str(value, bitwidth)
        case (val, int(prefix)):
            if prefix > bitwidth or prefix < 0:
                raise _InvalidErr("lpm", bitwidth, value)
            mask = ~all_ones(bitwidth - prefix)
            return (encode_exact(val, bitwidth, mask), prefix)
        case IPv4Network() | IPv6Network():
            if bitwidth != value.max_prefixlen:
                raise _InvalidErr("lpm", bitwidth, value)
            return (encode_exact(value.network_address, bitwidth), value.prefixlen)
        case IPv4Address() | IPv6Address():
            if bitwidth != value.max_prefixlen:
                raise _InvalidErr("lpm", bitwidth, value)
            return (encode_exact(value, bitwidth), bitwidth)
        case MACAddress():
            if bitwidth != 48:  # MACAddress is missing max_prefixlen.
                raise _InvalidErr("lpm", bitwidth, value)
            return (encode_exact(value, bitwidth), bitwidth)
        case _:
            raise _InvalidErr("lpm", bitwidth, value)


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


def format_lpm(value: _LPMValue, bitwidth: int, format: DecodeFormat) -> str:
    "Format a value as a string."

    data = encode_lpm(value, bitwidth)
    result = decode_lpm(data[0], data[1], bitwidth, format | DecodeFormat.STRING)
    assert isinstance(result, str)
    return result


# Ternary Values
# ~~~~~~~~~~~~~~
#
# Supported input values for `encode_ternary`:
#
# - int
# - str
#   o decimal integer [exact]
#   o hexadecimal integer (prefixed with `0x`) [exact]
#   o IPv4 string (bitwidth=32 only) [exact]
#   o IPv6 string (bitwidth=128 only) [exact]
#   o MAC string  (bitwidth=48 only) [exact]
#   o "value/prefix" where value is any of the above singular values
#   o "value/&mask" where value/mask is any of the above singular values
# - IPv4Address (bitwidth=32 only) [exact]
# - IPv6Address (bitwidth=128 only) [exact]
# - MACAddress (bitwidth=48 only) [exact]
# - IPv4Network (bitwidth=32 only)
# - IPv6Network (bitwidth=128 only)
# - tuple[value, mask]
#   o tuple[int, int]
#   o tuple[str, str]
#   o tuple[IPv4Address, IPv4Address] (bitwidth=32 only)
#   o tuple[IPv6Address, IPv6Address] (bitwidth=128 only)
#   o tuple[MACAddress, MACAddress]  (bitwidth=48 only)
#
# Supported output values for `decode_ternary`:
#
# - DEFAULT:
#   o tuple[int, int]
# - STRING:
#   o "value/&mask" with value, mask in hexadecimal
# - ADDRESS:
#   o tuple[IPv4Address, IPv4Address] (bitwidth=32)
#   o tuple[IPv6Address, IPv6Address] (bitwidth=128)
#   o tuple[MACAddress, MACAddress] (bitwidth=48)
#   o See DEFAULT output.
# - ADDRESS, STRING
#   o "IPV4/&mask"  (bitwidth=32)
#   o "IPV6/&mask"  (bitwidth=128)
#   o "MAC/&mask"   (bitwidth=48)
#   o See STRING output.

_TernaryValue = (
    SupportsInt | str | IPv4Network | IPv6Network | tuple[_ExactValue, _ExactValue]
)
_TernaryReturn = tuple[_ExactReturn, _ExactReturn] | _ExactReturn


def _parse_ternary_str(value: str, bitwidth: int) -> tuple[bytes, bytes]:
    "Parse value in slash or slash-amp notation."

    if "/&" not in value:
        data, prefix = _parse_lpm_str(value, bitwidth)
        mask = all_ones(prefix) << (bitwidth - prefix)
        return (data, encode_exact(mask, bitwidth))

    vals = value.split("/&", 1)

    # TODO: Masked bits in value must be zero.
    return (encode_exact(vals[0], bitwidth), encode_exact(vals[1], bitwidth))


def encode_ternary(value: _TernaryValue, bitwidth: int) -> tuple[bytes, bytes]:
    "Encode a value into a P4R ternary value."
    assert value is not None

    match value:
        case int(val):
            mask = all_ones(bitwidth)
        case str():
            return _parse_ternary_str(value, bitwidth)
        case (val, mask):
            pass
        case IPv4Network() | IPv6Network():
            val, mask = int(value.network_address), int(value.netmask)
        case IPv4Address() | IPv6Address():
            val = int(value)
            mask = all_ones(bitwidth)
        case _:
            raise _InvalidErr("ternary", bitwidth, value)

    # TODO: Masked bits in value must be zero.
    return (encode_exact(val, bitwidth), encode_exact(mask, bitwidth))


def decode_ternary(
    data: bytes,
    mask: bytes,
    bitwidth: int,
    hint: DecodeFormat = DecodeFormat.DEFAULT,
) -> _TernaryReturn:
    "Decode a P4R Ternary value."

    result = (decode_exact(data, bitwidth, hint), decode_exact(mask, bitwidth, hint))

    match result[0]:
        case str():
            return f"{result[0]}/&{result[1]}"
        case _:
            return result


def format_ternary(value: _TernaryValue, bitwidth: int, format: DecodeFormat) -> str:
    "Format a value as a string."

    data = encode_ternary(value, bitwidth)
    result = decode_ternary(data[0], data[1], bitwidth, format | DecodeFormat.STRING)
    assert isinstance(result, str)
    return result


# Range Values
# ~~~~~~~~~~~~
#
# Supported input values for `encode_range`:
#
# - str
#   o "lo...hi"
# - tuple[lo, hi]
#   o tuple[int, int]
#   o tuple[str, str]
#   o tuple[IPv4Address, IPv4Address] (bitwidth=32 only)
#   o tuple[IPv6Address, IPv6Address] (bitwidth=128 only)
#   o tuple[MACAddress, MACAddress]  (bitwidth=48 only)
#
# Supported output values for `decode_range`:
#
# - DEFAULT:
#   o tuple[int, int]
# - STRING:
#   o "lo...hi"
# - ADDRESS:
#   o See DEFAULT output.
# - ADDRESS, STRING
#   o See STRING output.

_RangeValue = str | tuple[_ExactValue, _ExactValue]
_RangeReturn = str | tuple[_ExactReturn, _ExactReturn]


def encode_range(value: _RangeValue, bitwidth: int) -> tuple[bytes, bytes]:
    "Encode a P4R Range value."
    assert value is not None

    match value:
        case str(val):
            low, high = val.split("...", 1)
        case (low, high):
            pass
        case _:
            raise _InvalidErr("range", bitwidth, value)

    return (encode_exact(low, bitwidth), encode_exact(high, bitwidth))


def decode_range(
    low: bytes,
    high: bytes,
    bitwidth: int,
    hint: DecodeFormat = DecodeFormat.DEFAULT,
) -> _RangeReturn:
    "Decode a P4R Range value."

    result = (decode_exact(low, bitwidth, hint), decode_exact(high, bitwidth, hint))

    match result[0]:
        case str():
            return f"{result[0]}...{result[1]}"
        case _:
            return result


def format_range(value: _RangeValue, bitwidth: int, format: DecodeFormat) -> str:
    "Format a value as a string."

    data = encode_range(value, bitwidth)
    result = decode_range(data[0], data[1], bitwidth, format | DecodeFormat.STRING)
    assert isinstance(result, str)
    return result
