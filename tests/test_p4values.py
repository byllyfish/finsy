from ipaddress import IPv4Network, IPv6Network
from ipaddress import ip_address as IP

import pytest
from finsy import p4values
from finsy.p4values import DecodeHint
from macaddress import MAC


def test_minimum_string_size():
    "Test the p4r_minimum_string_size function."

    for val, result in [(1, 1), (7, 1), (8, 1), (9, 2), (16, 2), (32, 4)]:
        assert p4values.p4r_minimum_string_size(val) == result

    for val in [0, -1]:
        with pytest.raises(ValueError):
            p4values.p4r_minimum_string_size(val)


def test_encode_exact():
    "Test the encode_exact function."

    # Decimal strings
    assert p4values.encode_exact("0", 32) == b"\x00"
    assert p4values.encode_exact("1", 32) == b"\x01"
    assert p4values.encode_exact("255", 32) == b"\xFF"
    assert p4values.encode_exact("256", 32) == b"\x01\x00"

    # Hexadecimal strings
    assert p4values.encode_exact("0x0", 32) == b"\x00"
    assert p4values.encode_exact("0x1", 32) == b"\x01"
    assert p4values.encode_exact("0x000ff", 32) == b"\xFF"
    assert p4values.encode_exact("0x100", 32) == b"\x01\x00"

    # Ints
    assert p4values.encode_exact(0, 32) == b"\x00"
    assert p4values.encode_exact(1, 32) == b"\x01"
    assert p4values.encode_exact(255, 32) == b"\xFF"
    assert p4values.encode_exact(256, 32) == b"\x01\x00"

    # Misc
    assert p4values.encode_exact(127, 7) == b"\x7F"
    assert p4values.encode_exact(4095, 12) == b"\x0f\xff"
    assert p4values.encode_exact(b"\x00\x00\x01", 4) == b"\x01"

    # Allow non-fractional float values.
    assert p4values.encode_exact(1.11e3, 12) == b"\x04\x56"


def test_encode_exact_fail():
    "Test the encode_exact function."

    with pytest.raises(ValueError, match="invalid value"):
        p4values.encode_exact("", 48)

    with pytest.raises(OverflowError):
        p4values.encode_exact("256", 8)

    with pytest.raises(OverflowError):
        p4values.encode_exact("128", 7)

    with pytest.raises(OverflowError):
        p4values.encode_exact("4096", 12)

    with pytest.raises(OverflowError):
        p4values.encode_exact("-1", 32)

    with pytest.raises(ValueError, match="Expected 4 octets"):
        p4values.encode_exact("10.0", 32)

    with pytest.raises(ValueError, match="invalid value"):
        p4values.encode_exact("10.0", 16)

    with pytest.raises(ValueError, match="fractional float value"):
        p4values.encode_exact(11.1, 32)

    with pytest.raises(ValueError, match="invalid value type"):
        p4values.encode_exact(1 + 2j, 32)  # type: ignore


def test_encode_exact_ip():
    "Test the encode_exact function with ip addresses."

    assert p4values.encode_exact("10.0.0.1", 32) == b"\x0A\x00\x00\x01"
    assert p4values.encode_exact(IP("10.0.0.1"), 32) == b"\x0A\x00\x00\x01"
    assert p4values.encode_exact("0.0.0.1", 32) == b"\x01"
    assert p4values.encode_exact(IP("0.0.0.1"), 32) == b"\x01"

    _IPV6 = b"\x20" + b"\x00" * 14 + b"\x01"
    assert p4values.encode_exact("2000::1", 128) == _IPV6
    assert p4values.encode_exact(IP("2000::1"), 128) == _IPV6
    assert p4values.encode_exact("::1", 128) == b"\x01"
    assert p4values.encode_exact(IP("::1"), 128) == b"\x01"

    # Ignore spaces.
    assert p4values.encode_exact(" 10.0.0.2 ", 32) == b"\x0A\x00\x00\x02"
    assert p4values.encode_exact(" 2000::1 ", 128) == _IPV6


def test_encode_exact_mac():
    "Test the encode_exact function with MAC addresses."

    _MAC = b"\x01\x00\x00\x00\x00\x01"
    assert p4values.encode_exact("01-00-00-00-00-01", 48) == _MAC
    assert p4values.encode_exact("01:00:00:00:00:01", 48) == _MAC
    assert p4values.encode_exact(MAC("01-00-00-00-00-01"), 48) == _MAC
    assert p4values.encode_exact("00-00-00-00-00-01", 48) == b"\x01"

    # Ignore spaces.
    assert p4values.encode_exact(" 01-00-00-00-00-01 ", 48) == _MAC


def test_encode_exact_to_spec():
    "Test the encode_exact function against values used in the P4R spec."

    # Examples from table 4.
    EXAMPLES = [
        (0x63, 8, b"\x63"),
        (0x63, 16, b"\x63"),
        (0x3064, 16, b"\x30\x64"),
        (0x63, 12, b"\x63"),
    ]

    for value, width, result in EXAMPLES:
        assert p4values.encode_exact(value, width) == result


def test_decode_exact_int():
    "Test the decode_exact function with the default hint."

    assert p4values.decode_exact(b"\x00", 32) == 0
    assert p4values.decode_exact(b"\x00\x00\x00\x00", 32) == 0
    assert p4values.decode_exact(b"\x01", 32) == 1
    assert p4values.decode_exact(b"\xFF", 32) == 255
    assert p4values.decode_exact(b"\x00\xFF", 32) == 255
    assert p4values.decode_exact(b"\x01\x00", 32) == 256

    assert p4values.decode_exact(b"\x01", 8, DecodeHint.ADDRESS) == 1


def test_decode_exact_mac():
    "Test the decode_exact function with a 'mac' hint."

    assert p4values.decode_exact(b"\x00", 48, DecodeHint.ADDRESS) == MAC(
        "00-00-00-00-00-00"
    )
    assert p4values.decode_exact(b"\x00\x00\x00", 48, DecodeHint.ADDRESS) == MAC(
        "00-00-00-00-00-00"
    )
    assert p4values.decode_exact(b"\x01", 48, DecodeHint.ADDRESS) == MAC(
        "00-00-00-00-00-01"
    )
    assert p4values.decode_exact(b"\xFF", 48, DecodeHint.ADDRESS) == MAC(
        "00-00-00-00-00-FF"
    )
    assert p4values.decode_exact(b"\x00\xFF", 48, DecodeHint.ADDRESS) == MAC(
        "00-00-00-00-00-FF"
    )
    assert p4values.decode_exact(b"\x01\x00", 48, DecodeHint.ADDRESS) == MAC(
        "00-00-00-00-01-00"
    )


def test_decode_exact_ip():
    "Test the decode_exact function with an 'ip' hint."

    assert p4values.decode_exact(b"\x00", 32, DecodeHint.ADDRESS) == IP("0.0.0.0")
    assert p4values.decode_exact(b"\x00\x00\x00", 32, DecodeHint.ADDRESS) == IP(
        "0.0.0.0"
    )
    assert p4values.decode_exact(b"\x01", 32, DecodeHint.ADDRESS) == IP("0.0.0.1")
    assert p4values.decode_exact(b"\xFF", 32, DecodeHint.ADDRESS) == IP("0.0.0.255")
    assert p4values.decode_exact(b"\x00\xFF", 32, DecodeHint.ADDRESS) == IP("0.0.0.255")
    assert p4values.decode_exact(b"\x01\x00", 32, DecodeHint.ADDRESS) == IP("0.0.1.0")

    _IPV6 = b"\x20" + b"\x00" * 14 + b"\x01"
    assert p4values.decode_exact(_IPV6, 128, DecodeHint.ADDRESS) == IP("2000::1")
    assert p4values.decode_exact(b"\x01", 128, DecodeHint.ADDRESS) == IP("::1")


def test_decode_exact_fail():
    "Test that the decode_exact function fails with improper input."

    with pytest.raises(ValueError, match="empty data"):
        p4values.decode_exact(b"", 8)

    with pytest.raises(OverflowError):
        p4values.decode_exact(b"\x01\x00", 8)

    with pytest.raises(ValueError, match="invalid hint"):
        p4values.decode_exact(b"\x01", 8, "x")  # type: ignore


def test_encode_lpm():
    "Test the encode_lpm function."

    # FIXME: Need 0 bits in low part...

    _IPV6 = b"\x20" + b"\x00" * 14 + b"\x01"
    assert p4values.encode_lpm("192.168.1.0/24", 32) == (b"\xc0\xa8\x01\x00", 24)
    assert p4values.encode_lpm("192.168.1.1/24", 32) == (b"\xc0\xa8\x01\x01", 24)
    assert p4values.encode_lpm("2000::1 / 64", 128) == (_IPV6, 64)
    assert p4values.encode_lpm("192.168.1.1", 32) == (b"\xc0\xa8\x01\x01", 32)

    assert p4values.encode_lpm(IPv4Network("192.168.1.0/24"), 32) == (
        b"\xc0\xa8\x01\x00",
        24,
    )
    assert p4values.encode_lpm(IPv6Network("2000::/64"), 128) == (
        b"\x20" + b"\x00" * 15,
        64,
    )

    assert p4values.encode_lpm(("192.168.1.0", 24), 32) == (
        b"\xc0\xa8\x01\x00",
        24,
    )
    assert p4values.encode_lpm(("2000::", 64), 128) == (
        b"\x20" + b"\x00" * 15,
        64,
    )


def test_encode_lpm_fail():
    "Test the encode_lpm function."

    with pytest.raises(ValueError, match="invalid value for bitwidth 16"):
        p4values.encode_lpm(IPv4Network("10.0.0.0/8"), 16)

    with pytest.raises(ValueError, match="invalid tuple value"):
        p4values.encode_lpm((1, 2, 3), 32)  # type: ignore

    with pytest.raises(ValueError, match="unexpected type"):
        p4values.encode_lpm(1 + 2j, 32)  # type: ignore

    with pytest.raises(ValueError, match="invalid prefix for bitwidth"):
        p4values.encode_lpm((1, 32), 8)


def test_decode_lpm():
    "Test the decode_lpm function."

    assert p4values.decode_lpm(b"\xc0\xa8\x01\x00", 24, 32, DecodeHint.ADDRESS) == (
        IP("192.168.1.0"),
        24,
    )
    assert p4values.decode_lpm(b"\xc0\xa8\x01\x01", 32, 32, DecodeHint.ADDRESS) == (
        IP("192.168.1.1"),
        32,
    )


def test_encode_ternary():
    "Test the encode_ternary function."

    assert p4values.encode_ternary((1, 1), 32) == (b"\x01", b"\x01")
    assert p4values.encode_ternary("192.168.1.1/255.255.255.0", 32) == (
        b"\xc0\xa8\x01\x01",
        b"\xff\xff\xff\x00",
    )

    # FIXME: This does not do what you think it should?
    assert p4values.encode_ternary("192.168.1.1/24", 32) == (
        b"\xc0\xa8\x01\x01",
        b"\x18",
    )

    # FIXME: This does not do what you think it should?
    assert p4values.encode_ternary("2000::1/64", 128) == (
        b"\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01",
        b"\x40",
    )

    assert p4values.encode_ternary(IPv4Network("10.0.0.0/24"), 32) == (
        b"\x0A\x00\x00\x00",
        b"\xff\xff\xff\x00",
    )

    assert p4values.encode_ternary(IPv6Network("2000::/64"), 128) == (
        b"\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
        b"\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00",
    )


def test_encode_ternary_fail():
    "Test the encode_ternary function."

    with pytest.raises(ValueError, match="unexpected value"):
        p4values.encode_ternary(1 + 2j, 32)  # type: ignore


def test_decode_ternary():
    "Test the decode_ternary function."

    assert p4values.decode_ternary(b"\x01", b"\x01", 32) == (1, 1)
    assert p4values.decode_ternary(b"\xc0\xa8\x01\x01", b"\xff\xff\xff\x00", 32) == (
        3232235777,
        4294967040,
    )


def test_decode_ternary_ip():
    "Test the decode_ternary function."

    assert p4values.decode_ternary(b"\x01", b"\x01", 32, DecodeHint.ADDRESS) == (
        IP("0.0.0.1"),
        IP("0.0.0.1"),
    )
    assert p4values.decode_ternary(
        b"\xc0\xa8\x01\x01", b"\xff\xff\xff\x00", 32, DecodeHint.ADDRESS
    ) == (IP("192.168.1.1"), IP("255.255.255.0"))

    assert p4values.decode_ternary(
        b"\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
        b"\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00",
        128,
        DecodeHint.ADDRESS,
    ) == (IP("2000::"), IP("ffff:ffff:ffff:ffff::"))


def test_encode_range():
    "Test the encode_range function."

    assert p4values.encode_range((1, 2), 32) == (b"\x01", b"\x02")
    assert p4values.encode_range("1-2", 32) == (b"\x01", b"\x02")
    assert p4values.encode_range((IP("1.2.3.4"), IP("1.2.3.5")), 32) == (
        b"\x01\x02\x03\x04",
        b"\x01\x02\x03\x05",
    )


def test_encode_range_fail():
    "Test the encode_range function."

    with pytest.raises(ValueError, match="unexpected value"):
        p4values.encode_range(1 + 2j, 32)  # type: ignore


def test_decode_range():
    "Test the decode_range function."

    assert p4values.decode_range(b"\x01", b"\x02", 32) == (1, 2)
    assert p4values.decode_range(
        b"\x01\x02\x03\x04", b"\x01\x02\x03\x05", 32, DecodeHint.ADDRESS
    ) == (IP("1.2.3.4"), IP("1.2.3.5"))
