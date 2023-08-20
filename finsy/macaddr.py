"Implements the MACAddress class."

# Copyright (c) 2022-2023 Bill Fisher
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

import functools

from typing_extensions import Self

_BYTE_WIDTH = 6
_BIT_WIDTH = _BYTE_WIDTH * 8


@functools.total_ordering
class MACAddress:
    """Concrete class for a MAC address."""

    __slots__ = ("_mac", "__weakref__")
    _mac: int

    def __init__(self, value: object) -> None:
        "Construct a MAC address from a string, integer or bytes object."
        match value:
            case int():
                self._mac = _from_int(value)
            case bytes():
                self._mac = _from_bytes(value)
            case MACAddress():
                self._mac = value._mac
            case _:
                # Input argument is a MAC string, or an object that is
                # formatted as MAC string (behave like ipaddress module).
                self._mac = _from_string(str(value))

    @property
    def packed(self) -> bytes:
        "Return the MAC address a byte string."
        return _to_bytes(self._mac)

    @property
    def max_prefixlen(self) -> int:
        "Return the maximum prefix length (48 bits)."
        return _BIT_WIDTH

    @property
    def is_multicast(self) -> bool:
        "Return true if MAC address has the multicast bit set."
        return self._mac & (1 << 40) != 0

    @property
    def is_private(self) -> bool:
        "Return true if MAC address has the locally administered bit set."
        return self._mac & (1 << 41) != 0

    @property
    def is_global(self) -> bool:
        "Return true if the locally administered bit is not set."
        return not self.is_private

    @property
    def is_unspecified(self) -> bool:
        "Return true if MAC address is all zeros."
        return self._mac == 0

    @property
    def is_broadcast(self) -> bool:
        "Return true if MAC address is the broadcast address."
        return self._mac == (1 << _BIT_WIDTH) - 1

    def __int__(self) -> int:
        return self._mac

    def __eq__(self, rhs: Self) -> bool:
        try:
            return self._mac == rhs._mac
        except AttributeError:
            return NotImplemented

    def __lt__(self, rhs: Self) -> bool:
        if not isinstance(rhs, MACAddress):
            return NotImplemented
        return self._mac < rhs._mac

    def __repr__(self) -> str:
        return f"MACAddress({_to_string(self._mac)!r})"

    def __str__(self) -> str:
        return _to_string(self._mac)

    def __hash__(self) -> int:
        return hash(hex(self._mac))


def _from_string(value: str) -> int:
    """Parse a MAC address string and return an integer representation.

    Args:
        value: A string of the form "hh:hh:hh:hh:hh:hh" or "hh-hh-hh-hh-hh-hh".
          where `hh` is 1-2 hexadecimal digits.

    Returns:
        The MAC address as an integer.

    Raises:
        ValueError: String value is invalid.
    """
    try:
        delimiter = "-" if "-" in value else ":"
        data = bytes(_parse_octet(octet) for octet in value.split(delimiter))
        return _from_bytes(data)
    except ValueError:
        pass

    raise ValueError(f"invalid MAC address: {value!r}")


def _parse_octet(value: str) -> int:
    "Parse a 2-char octet in string format."
    length = len(value)
    if length == 1 or length == 2 == len(value.strip()):
        # Be careful because int() will accept/ignore space chars.
        return int(value, 16)
    raise ValueError("invalid octet")


def _from_bytes(value: bytes) -> int:
    "Convert 6-bytes to integer."
    if len(value) != _BYTE_WIDTH:
        raise ValueError(f"invalid MAC address: {value!r}")
    return int.from_bytes(value, byteorder="big")


def _from_int(value: int) -> int:
    "Check that integer value for MAC address is in range."
    if value < 0 or value > (1 << _BIT_WIDTH) - 1:
        raise ValueError(f"invalid MAC address: {value!r}")
    return value


def _to_string(value: int) -> str:
    "Convert integer MAC address value to string."
    return ":".join(f"{octet:02x}" for octet in _to_bytes(value))


def _to_bytes(value: int) -> bytes:
    "Convert integer MAC address value to bytes."
    return value.to_bytes(_BYTE_WIDTH, byteorder="big")
