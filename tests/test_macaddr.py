"Test the MACAddress class."

import pytest

from finsy import MACAddress


def test_constructor():
    "Test the MACAddress constructor."
    assert int(MACAddress(1)) == 1
    assert int(MACAddress(1 << 47)) == (1 << 47)
    assert int(MACAddress((1 << 48) - 1)) == (1 << 48) - 1
    assert int(MACAddress("00:00:00:00:00:01")) == 1
    assert int(MACAddress("00-00-00-00-00-01")) == 1
    assert int(MACAddress(b"\x00\x00\x00\x00\x00\x01")) == 1

    addr = MACAddress(1)
    assert int(MACAddress(addr)) == 1


def test_constructor_valid():
    "Test the MACAddress constructor with valid string arguments."
    values = ["0:0:0:0:0:1", "00:00:00:0:00:1", "00-00-00-0-00-1"]
    for value in values:
        assert int(MACAddress(value)) == 1


def test_constructor_invalid():
    "Test the MACAddress constructor with invalid arguments."
    values = [
        "00.00.00.00.00.01",
        " 00:00:00:00:00:01",
        "00:00:00:00:00:01 ",
        "00:00:00:00:01",
        "00:00:00:00:00:0001",
        "00:00:00: 0:00:01",
        "00:00:00-00:00:01",
        "00:00:0g:00:00:01",
        -1,
        b"\x01",
        1 << 48,
        1j,
        1.0,
    ]

    for value in values:
        with pytest.raises(ValueError, match="invalid MAC address"):
            MACAddress(value)


def test_is_multicast():
    "Test the `is_multicast` property."
    assert MACAddress("FF:FF:00:00:00:00").is_multicast
    assert not MACAddress("FE:FF:00:00:00:00").is_multicast


def test_is_private():
    "Test the `is_private` property."
    assert MACAddress("FF:FF:00:00:00:00").is_private
    assert not MACAddress("FD:FF:00:00:00:00").is_private


def test_is_global():
    "Test the `is_global` property."
    assert not MACAddress("FF:FF:00:00:00:00").is_global
    assert MACAddress("FD:FF:00:00:00:00").is_global


def test_is_broadcast():
    "Test the `is_broadcast` property."
    assert MACAddress("FF:FF:FF:FF:FF:FF").is_broadcast
    assert not MACAddress("FF:FF:FF:FF:FF:FE").is_broadcast


def test_is_unspecified():
    "Test the `is_broadcast` property."
    assert MACAddress(0).is_unspecified
    assert not MACAddress(1).is_unspecified


def test_packed():
    "Test the `packed` property."
    assert MACAddress(0).packed == b"\x00\x00\x00\x00\x00\x00"
    assert MACAddress(0xFFFFFFFFFFFF).packed == b"\xFF\xFF\xFF\xFF\xFF\xFF"


def test_eq():
    "Test the `__eq__` method."
    a = MACAddress(1)
    b = MACAddress(1)
    c = MACAddress(2)
    assert a == b
    assert a != c
    assert not (a == 1)


def test_lt():
    "Test the `__lt__` method."
    a = MACAddress(1)
    b = MACAddress(1)
    c = MACAddress(2)
    assert not a < b
    assert a < c

    with pytest.raises(TypeError, match="not supported"):
        assert a < 2


def test_str():
    "Test the `__str__` method."
    assert str(MACAddress(1)) == "00:00:00:00:00:01"
    assert str(MACAddress(0xFFFFFFFFFFFF)) == "ff:ff:ff:ff:ff:ff"


def test_repr():
    "Test the `__repr__` method."
    assert repr(MACAddress(1)) == "MACAddress('00:00:00:00:00:01')"
    assert repr(MACAddress(0xFFFFFFFFFFFF)) == "MACAddress('ff:ff:ff:ff:ff:ff')"


def test_max_prefixlen():
    "Test the `max_prefixlen` property."
    assert MACAddress(1).max_prefixlen == 48


def test_hash():
    "Test the `__hash__` method."
    assert hash(MACAddress(1)) == hash(MACAddress(1))
    assert hash(MACAddress(1)) != hash(MACAddress(2))
