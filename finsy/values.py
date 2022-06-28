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

from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from typing import Literal, SupportsInt

from macaddress import MAC as MACAddress

_DecodeHint = Literal["ip", "mac"] | None  # FIXME: use enum

_ExactValue = SupportsInt | str | bytes
_ExactReturn = int | IPv4Address | IPv6Address | MACAddress

_LPMValue = str | IPv4Network | IPv6Network | tuple[_ExactValue, int]
_LPMReturn = IPv4Network | IPv6Network | tuple[_ExactReturn, int]

_TernaryValue = str | tuple[_ExactValue, _ExactValue]
_TernaryReturn = tuple[_ExactReturn, _ExactReturn]

_OptionalValue = _ExactValue | None
_OptionalReturn = _ExactReturn | None


def p4r_minimum_string_size(bitwidth: int) -> int:
    "P4Runtime `minimum_string_size` function (P4R-Spec section 8.4)"
    if bitwidth <= 0:
        raise ValueError(f"invalid bitwidth: {bitwidth}")
    return (bitwidth + 7) // 8


def p4r_truncate(value: bytes, signed: bool = False) -> bytes:
    "Truncate a bytes value to the specified bitwidth."
    assert not signed, "TODO: signed not yet supported"
    result = value.lstrip(b"\x00")
    return result if result else b"\x00"


def encode_exact(value: _ExactValue, bitwidth: int) -> bytes:
    "Encode an exact field value into a byte encoding."

    if isinstance(value, bytes):
        if len(value) * 8 != bitwidth:
            raise ValueError(f"invalid value for bitwidth {bitwidth}: {value!r}")
        return p4r_truncate(value)

    if isinstance(value, str):
        value = value.strip()

        # Handle common string conversions.
        if bitwidth == 32 and "." in value:
            ival = int(IPv4Address(value))
        elif bitwidth == 128 and ":" in value:
            ival = int(IPv6Address(value))
        elif bitwidth == 48 and ("-" in value[1:] or ":" in value):
            ival = int(MACAddress(value))
        else:
            try:
                ival = int(value, base=0)
            except ValueError as ex:
                raise ValueError(
                    f"invalid value for bitwidth {bitwidth}: {value!r}"
                ) from None

    elif isinstance(value, SupportsInt):
        if isinstance(value, float) and not value.is_integer():
            raise ValueError(f"fractional float value: {value!r}")
        # Handle int, non-fractional float and IP address objects.
        ival = int(value)

    else:
        raise ValueError(f"invalid value type: {value!r}")

    if ival >= (1 << bitwidth):
        raise OverflowError(f"invalid value for bitwidth {bitwidth}: {value!r}")

    size = p4r_minimum_string_size(bitwidth)
    bval = ival.to_bytes(size, "big")
    return p4r_truncate(bval)


def decode_exact(
    data: bytes,
    bitwidth: int,
    hint: _DecodeHint = None,
) -> _ExactReturn:
    """Decode a P4R value into an integer or address."""
    if not data:
        raise ValueError("empty data")

    ival = int.from_bytes(data, "big")
    if ival >= (1 << bitwidth):
        raise OverflowError(f"invalid value for bitwidth {bitwidth}: {data!r}")

    match hint:
        case None:
            return ival
        case "ip":
            if bitwidth > 32:
                return IPv6Address(ival)
            else:
                return IPv4Address(ival)
        case "mac":
            return MACAddress(ival)
        case other:
            raise ValueError(f"invalid hint: {other!r}")


def encode_lpm(value: _LPMValue, bitwidth: int) -> tuple[bytes, int]:
    "Encode a string value into a P4R LPM value."
    if isinstance(value, (IPv4Network, IPv6Network)):
        if bitwidth != value.max_prefixlen:
            raise ValueError(f"invalid value for bitwidth {bitwidth}: {value!r}")
        data = encode_exact(value.network_address, bitwidth)
        return data, value.prefixlen

    if isinstance(value, str):
        vals = value.split("/", 1)
    elif isinstance(value, tuple):
        if len(value) != 2:
            raise ValueError(f"invalid tuple value: {value!r}")
        vals = value

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
    hint: _DecodeHint = None,
) -> _LPMReturn:
    "Decode a P4R Value into an integer or address."
    addr = decode_exact(data, bitwidth, hint)
    if isinstance(addr, IPv4Address):
        return IPv4Network((addr, prefix_len))
    if isinstance(addr, IPv6Address):
        return IPv6Network((addr, prefix_len))
    return (addr, prefix_len)


def encode_ternary(value: _TernaryValue, bitwidth: int) -> tuple[bytes, bytes]:
    "TODO: Not implemented yet."
    raise NotImplementedError("TODO")


def decode_ternary(
    data: bytes,
    mask: bytes,
    bitwidth: int,
    hint: _DecodeHint = None,
) -> _TernaryReturn:
    "TODO: Not implemented yet."
    raise NotImplementedError("TODO")


def encode_optional(value: _OptionalValue, bitwidth: int) -> bytes:
    "TODO: Not implemented yet."
    raise NotImplementedError("TODO")


def decode_optional(
    data: bytes,
    bitwidth: int,
    hint: _DecodeHint = None,
) -> _OptionalReturn:
    "TODO: Not implemented yet."
    raise NotImplementedError("TODO")
