from ipaddress import IPv4Network, IPv6Network
from ipaddress import ip_address as IP
from typing import Any

import pytest

from finsy import p4values
from finsy.macaddr import MACAddress
from finsy.p4values import DecodeFormat

ADDR_STR = DecodeFormat.ADDRESS | DecodeFormat.STRING


def test_minimum_string_size():
    "Test the p4r_minimum_string_size function."
    for val, result in [(1, 1), (7, 1), (8, 1), (9, 2), (16, 2), (32, 4)]:
        assert p4values.p4r_minimum_string_size(val) == result

    for val in [0, -1]:
        with pytest.raises(ValueError):
            p4values.p4r_minimum_string_size(val)


def test_all_ones():
    "Test the all_ones function."
    for val, result in [(0, 0), (1, 1), (2, 3), (8, 0xFF), (9, 0x1FF)]:
        assert p4values.all_ones(val) == result


def test_mask_to_prefix():
    "Test the mask_to_prefix function."
    data = [
        (0x0F, 4, 4),
        (0x0E, 4, 3),
        (0x0C, 4, 2),
        (0x08, 4, 1),
        (0x00, 4, 0),
        (0xFF00, 16, 8),
        (0xFEF0, 16, -1),
        (0x1FFFF, 17, 17),
        (0x1FFFF, 18, -1),
    ]

    for val, bitwidth, result in data:
        assert p4values.mask_to_prefix(val, bitwidth) == result


def test_p4r_truncate():
    "Test the p4r_truncate function."
    assert p4values.p4r_truncate(b"\x00") == b"\x00"
    assert p4values.p4r_truncate(b"\x80") == b"\x80"
    assert p4values.p4r_truncate(b"\xFF") == b"\xFF"
    assert p4values.p4r_truncate(b"\x00\x80") == b"\x80"
    assert p4values.p4r_truncate(b"\x80\x80") == b"\x80\x80"
    assert p4values.p4r_truncate(b"\xFF\x80") == b"\xFF\x80"
    assert p4values.p4r_truncate(b"\xFF\xFF") == b"\xFF\xFF"


def test_p4r_truncate_signed():
    "Test the p4r_truncate_signed function."
    assert p4values.p4r_truncate_signed(b"\x00") == b"\x00"
    assert p4values.p4r_truncate_signed(b"\x80") == b"\x80"
    assert p4values.p4r_truncate_signed(b"\xFF") == b"\xFF"
    assert p4values.p4r_truncate_signed(b"\x00\x80") == b"\x00\x80"
    assert p4values.p4r_truncate_signed(b"\x80\x80") == b"\x80\x80"
    assert p4values.p4r_truncate_signed(b"\xFF\x80") == b"\x80"
    assert p4values.p4r_truncate_signed(b"\xFF\xFF") == b"\xFF"
    assert p4values.p4r_truncate_signed(b"\x80\xFF\xFF") == b"\x80\xFF\xFF"
    assert p4values.p4r_truncate_signed(b"\x7F\xFF\xFF") == b"\x7F\xFF\xFF"


def test_encode_exact_int():
    "Test the encode_exact function."
    data = [
        # Ints
        (0, 32, b"\x00"),
        (1, 32, b"\x01"),
        (255, 32, b"\xFF"),
        (256, 32, b"\x01\x00"),
        # Decimal strings
        ("0", 32, b"\x00"),
        ("1", 32, b"\x01"),
        ("255", 32, b"\xFF"),
        ("256", 32, b"\x01\x00"),
        # Hex strings
        ("0x0", 32, b"\x00"),
        ("0x1", 32, b"\x01"),
        ("0x000ff", 32, b"\xFF"),
        ("0x100", 32, b"\x01\x00"),
        # Misc.
        (127, 7, b"\x7F"),
        (4095, 12, b"\x0f\xff"),
    ]

    for value, bitwidth, result in data:
        assert p4values.encode_exact(value, bitwidth) == result


def test_encode_exact_fail():
    "Test the encode_exact function."
    data = [
        ("", 48),
        ("256", 8),
        ("128", 7),
        ("-1", 32),
        ("10.0", 32),
        ("10.0", 16),
        (10.0, 32),
        (1 + 2j, 32),
        ("0.0.0.1", 8),
        (IP("0.0.0.1"), 8),
        (IP("::1"), 32),
        (MACAddress("0e-00-00-00-00-01"), 32),
    ]

    for value, bitwidth in data:
        with pytest.raises(ValueError):
            p4values.encode_exact(value, bitwidth)  # type: ignore


def test_encode_exact_ipv4():
    "Test the encode_exact function with IPv4 addresses."
    data = [
        ("10.0.0.1", b"\x0A\x00\x00\x01"),
        ("0.0.0.1", b"\x01"),
        (" 10.0.0.2 ", b"\x0A\x00\x00\x02"),  # ignore spaces
        (IP("10.0.0.1"), b"\x0A\x00\x00\x01"),
        (IP("0.0.0.1"), b"\x01"),
    ]

    for value, result in data:
        assert p4values.encode_exact(value, 32) == result


def test_encode_exact_ipv6():
    "Test the encode_exact function with IPv6 addresses."
    _IPV6 = b"\x20" + b"\x00" * 14 + b"\x01"
    data = [
        ("2000::1", _IPV6),
        ("::1", b"\x01"),
        (" 2000::1 ", _IPV6),  # ignore spaces
        (IP("2000::1"), _IPV6),
        (IP("::1"), b"\x01"),
    ]

    for value, result in data:
        assert p4values.encode_exact(value, 128) == result


def test_encode_exact_mac():
    "Test the encode_exact function with MAC addresses."
    _MAC = b"\x01\x00\x00\x00\x00\x01"

    data = [
        ("01-00-00-00-00-01", _MAC),
        ("01:00:00:00:00:01", _MAC),
        ("00-00-00-00-00-01", b"\x01"),
        (" 01-00-00-00-00-01 ", _MAC),  # ignore spaces
        (MACAddress("01-00-00-00-00-01"), _MAC),
    ]

    for value, result in data:
        assert p4values.encode_exact(value, 48) == result


def test_encode_exact_to_spec():
    "Test the encode_exact function against values used in the P4R spec."
    # Examples from table 4.
    data = [
        (0x63, 8, b"\x63"),
        (0x63, 16, b"\x63"),
        (0x3064, 16, b"\x30\x64"),
        (0x63, 12, b"\x63"),
    ]

    for value, width, result in data:
        assert p4values.encode_exact(value, width) == result


def test_encode_exact_sdnstring():
    "Test the encode_exact function with a bitwidth of zero."
    data = [
        ("abc", b"abc"),
        ("x", b"x"),
        ("", b""),  # supported for now
    ]

    for value, result in data:
        assert p4values.encode_exact(value, 0) == result


def test_decode_exact_int():
    "Test the decode_exact function with 31-bit integer values."
    data = [
        (b"\x00", 0),
        (b"\x00\x00\x00\x00", 0),
        (b"\x01", 1),
        (b"\xFF", 255),
        (b"\x00\xFF", 255),
        (b"\x01\x00", 256),
    ]

    for value, result in data:
        assert p4values.decode_exact(value, 31) == result
        assert p4values.decode_exact(value, 31, DecodeFormat.STRING) == hex(result)
        assert p4values.decode_exact(value, 31, DecodeFormat.ADDRESS) == result
        assert p4values.decode_exact(value, 31, ADDR_STR) == hex(result)

    for value, result in data:
        assert p4values.encode_exact(result, 31) == p4values.p4r_truncate(value)
        assert p4values.encode_exact(int(result), 31) == p4values.p4r_truncate(value)
        assert p4values.encode_exact(hex(result), 31) == p4values.p4r_truncate(value)


def test_decode_exact_mac():
    "Test the decode_exact function with MAC address values."
    data = [
        (b"\x00", "00:00:00:00:00:00"),
        (b"\x00\x00\x00", "00:00:00:00:00:00"),
        (b"\x01", "00:00:00:00:00:01"),
        (b"\xFF", "00:00:00:00:00:ff"),
        (b"\x00\xFF", "00:00:00:00:00:ff"),
        (b"\x01\x00", "00:00:00:00:01:00"),
    ]

    for value, result in data:
        assert p4values.decode_exact(value, 48, DecodeFormat.ADDRESS) == MACAddress(
            result
        )
        assert p4values.decode_exact(value, 48, ADDR_STR) == result

    for value, result in data:
        assert p4values.encode_exact(result, 48) == p4values.p4r_truncate(value)
        assert p4values.encode_exact(MACAddress(result), 48) == p4values.p4r_truncate(
            value
        )


def test_decode_exact_ipv4():
    "Test the decode_exact function with 32-bit IPv4 address values."
    data = [
        (b"\x00", "0.0.0.0"),
        (b"\x00\x00\x00", "0.0.0.0"),
        (b"\x01", "0.0.0.1"),
        (b"\xFF", "0.0.0.255"),
        (b"\x00\xFF", "0.0.0.255"),
        (b"\x01\x00", "0.0.1.0"),
    ]

    for value, result in data:
        assert p4values.decode_exact(value, 32, DecodeFormat.ADDRESS) == IP(result)
        assert p4values.decode_exact(value, 32, ADDR_STR) == result

    for value, result in data:
        assert p4values.encode_exact(result, 32) == p4values.p4r_truncate(value)
        assert p4values.encode_exact(IP(result), 32) == p4values.p4r_truncate(value)


def test_decode_exact_ipv6():
    "Test the decode_exact function with 128-bit IPv6 address values."
    data = [
        (b"\x20" + b"\x00" * 14 + b"\x01", "2000::1"),
        (b"\x01", "::1"),
        (b"\x00", "::"),
    ]

    for value, result in data:
        assert p4values.decode_exact(value, 128, DecodeFormat.ADDRESS) == IP(result)
        assert p4values.decode_exact(value, 128, ADDR_STR) == result

    for value, result in data:
        assert p4values.encode_exact(result, 128) == p4values.p4r_truncate(value)
        assert p4values.encode_exact(IP(result), 128) == p4values.p4r_truncate(value)


def test_decode_exact_fail():
    "Test that the decode_exact function fails with improper input."
    data = [
        (b"", 8),
        (b"\x01\x00", 8),
    ]

    for value, bitwidth in data:
        with pytest.raises(ValueError):
            p4values.decode_exact(value, bitwidth)


def test_decode_exact_sdnstring():
    "Test the decode_exact function with a bitwidth=0."
    data = [
        ("abc", b"abc"),
        ("x", b"x"),
        ("", b""),  # supported for now
    ]

    for result, value in data:
        assert p4values.decode_exact(value, 0) == result


def test_encode_lpm_exact():
    "Test the encode_lpm function."
    data = [
        (1, 32, (b"\x01", 32)),
        ((0x80, 7), 8, (b"\x80", 7)),
        (("0x80", 7), 8, (b"\x80", 7)),
        ("1", 32, (b"\x01", 32)),
        ("0x1", 32, (b"\x01", 32)),
        ("0x80/7", 8, (b"\x80", 7)),
        ("128/7", 8, (b"\x80", 7)),
    ]

    for value, bitwidth, result in data:
        assert p4values.encode_lpm(value, bitwidth) == result


def test_encode_lpm_ipv4():
    "Test the encode_lpm function."
    data = [
        ("192.168.1.1", (b"\xc0\xa8\x01\x01", 32)),
        (IP("192.168.1.1"), (b"\xc0\xa8\x01\x01", 32)),
        ("192.168.1.0/24", (b"\xc0\xa8\x01\x00", 24)),
        (" 192.168.1.0/24 ", (b"\xc0\xa8\x01\x00", 24)),  # ignore spaces
        ("192.168.1.1/24", (b"\xc0\xa8\x01\x00", 24)),
        (("192.168.1.0", 24), (b"\xc0\xa8\x01\x00", 24)),
        ((IP("192.168.1.0"), 24), (b"\xc0\xa8\x01\x00", 24)),
        ((IP("192.168.1.1"), 24), (b"\xc0\xa8\x01\x00", 24)),
        (IPv4Network("192.168.1.0/24"), (b"\xc0\xa8\x01\x00", 24)),
        ("192.168.0.1/255.255.0.0", (b"\xc0\xa8\x00\x00", 16)),
    ]

    for value, result in data:
        assert p4values.encode_lpm(value, 32) == result


def test_encode_lpm_ipv6():
    "Test the encode_lpm function."
    _IPV6 = b"\x20" + b"\x00" * 14 + b"\x01"
    _IPP6 = b"\x20" + b"\x00" * 15
    data = [
        ("2000::1", (_IPV6, 128)),
        (IP("2000::1"), (_IPV6, 128)),
        ("2000::1/64", (_IPP6, 64)),
        (" 2000::/64 ", (_IPP6, 64)),  # ignore spaces
        (("2000::", 64), (_IPP6, 64)),
        ((IP("2000::"), 64), (_IPP6, 64)),
        ((IP("2000::1"), 64), (_IPP6, 64)),
        (IPv6Network("2000::/64"), (_IPP6, 64)),
        ("2000::1/ffff::", (_IPP6, 16)),
    ]

    for value, result in data:
        assert p4values.encode_lpm(value, 128) == result


def test_encode_lpm_mac():
    "Test the encode_lpm function."
    data = [
        ("0e:00:00:00:00:01", (b"\x0e\x00\x00\x00\x00\x01", 48)),
        (MACAddress("0e:00:00:00:00:01"), (b"\x0e\x00\x00\x00\x00\x01", 48)),
        ("0e:00:00:00:00:01/24", (b"\x0e\x00\x00\x00\x00\x00", 24)),
        (" 0e:00:00:00:00:01/24 ", (b"\x0e\x00\x00\x00\x00\x00", 24)),  # ignore spaces
        ("0e:00:00:00:00:01/ff:ff:ff:00:00:00", (b"\x0e\x00\x00\x00\x00\x00", 24)),
    ]

    for value, result in data:
        assert p4values.encode_lpm(value, 48) == result


def test_encode_lpm_fail():
    "Test the encode_lpm function."
    data = [
        (IPv4Network("10.0.0.0/8"), 16),
        ((1, 2, 3), 32),
        (1 + 2j, 32),
        ((1, 32), 8),
        ("127.0.0.1/33", 32),
        ("127.0.0.1", 8),
        (IP("127.0.0.1"), 8),
        (IP("::1"), 32),
        (MACAddress("0e:00:00:00:00:01"), 32),
        ("abc", 0),  # SdnString not supported
    ]

    for value, bitwidth in data:
        with pytest.raises(ValueError):
            p4values.encode_lpm(value, bitwidth)  # type: ignore


def test_decode_lpm_int():
    "Test the decode_lpm function."
    data = [
        # All bitwidth's are 33.
        (b"\x00", 32, 33, (0, 32)),
        (b"\x00\x00\x00\x00", 32, 33, (0, 32)),
        (b"\x02", 32, 33, (2, 32)),
        (b"\xFE", 32, 33, (254, 32)),
        (b"\x00\xFE", 32, 33, (254, 32)),
        (b"\x01\x00", 32, 33, (256, 32)),
    ]

    def _to_str(val: tuple[int, int]):
        return f"{hex(val[0])}/{val[1]}"

    for value, prefix, bitwidth, result in data:
        assert p4values.decode_lpm(value, prefix, bitwidth) == result
        assert p4values.decode_lpm(
            value, prefix, bitwidth, DecodeFormat.STRING
        ) == _to_str(result)
        assert p4values.decode_lpm(value, prefix, bitwidth, ADDR_STR) == _to_str(result)

    for value, prefix, bitwidth, result in data:
        assert p4values.encode_lpm(result, bitwidth) == (
            p4values.p4r_truncate(value),
            prefix,
        )


def test_decode_lpm_ipv4():
    "Test the decode_lpm function."
    data = [
        (b"\xc0\xa8\x01\x00", 24, IPv4Network("192.168.1.0/24"), "192.168.1.0/24"),
        (b"\xc0\xa8\x01\x01", 32, IPv4Network("192.168.1.1/32"), "192.168.1.1"),
    ]

    for value, prefix, result, res_str in data:
        assert p4values.decode_lpm(value, prefix, 32, DecodeFormat.ADDRESS) == result
        assert p4values.decode_lpm(value, prefix, 32, ADDR_STR) == res_str

    for value, prefix, result, _ in data:
        assert p4values.encode_lpm(result, 32) == (value, prefix)
        assert p4values.encode_lpm(str(result), 32) == (value, prefix)


def test_decode_lpm_ipv6():
    "Test the decode_lpm function."
    _IPV6 = b"\x20" + b"\x00" * 14 + b"\x01"
    _IPP6 = b"\x20" + b"\x00" * 15
    data = [
        (_IPP6, 64, IPv6Network("2000::/64"), "2000::/64"),
        (_IPV6, 128, IPv6Network("2000::1/128"), "2000::1"),
    ]

    for value, prefix, result, res_str in data:
        assert p4values.decode_lpm(value, prefix, 128, DecodeFormat.ADDRESS) == result
        assert p4values.decode_lpm(value, prefix, 128, ADDR_STR) == res_str

    for value, prefix, result, _ in data:
        assert p4values.encode_lpm(result, 128) == (value, prefix)
        assert p4values.encode_lpm(str(result), 128) == (value, prefix)


def test_encode_ternary_int():
    "Test the encode_ternary function."
    data = [
        (0, 8, (b"\x00", b"\xff")),
        (3, 4, (b"\x03", b"\x0f")),
        ((1, 1), 32, (b"\x01", b"\x01")),
        ((2, 1), 32, (b"\x02", b"\x01")),  # technically invalid...
        ("3", 4, (b"\x03", b"\x0f")),
        ("0x3", 4, (b"\x03", b"\x0f")),
        ("0x30/4", 8, (b"\x30", b"\xf0")),
        ("0x30/&0x30", 8, (b"\x30", b"\x30")),
    ]

    for value, bitwidth, result in data:
        assert p4values.encode_ternary(value, bitwidth) == result


def test_encode_ternary_ipv4():
    "Test the encode_ternary function."
    data = [
        ("192.168.1.1", (b"\xc0\xa8\x01\x01", b"\xff\xff\xff\xff")),
        (IP("192.168.1.1"), (b"\xc0\xa8\x01\x01", b"\xff\xff\xff\xff")),
        (
            "192.168.1.1/255.255.255.0",
            (b"\xc0\xa8\x01\x00", b"\xff\xff\xff\x00"),
        ),
        ("192.168.1.1/24", (b"\xc0\xa8\x01\x00", b"\xff\xff\xff\x00")),
        (IPv4Network("10.0.0.0/24"), (b"\x0A\x00\x00\x00", b"\xff\xff\xff\x00")),
    ]

    for value, result in data:
        assert p4values.encode_ternary(value, 32) == result


def test_encode_ternary_ipv6():
    "Test the encode_ternary function."
    data = [
        (
            "2000::1",
            (
                b"\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01",
                b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff",
            ),
        ),
        (
            IP("2000::1"),
            (
                b"\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01",
                b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff",
            ),
        ),
        (
            "2000::1/64",
            (
                b" \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
                b"\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00",
            ),
        ),
        (
            IPv6Network("2000::/64"),
            (
                b"\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
                b"\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00",
            ),
        ),
        (
            "2000::1/ffff::",
            (
                b" \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
                b"\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
            ),
        ),
    ]

    for value, result in data:
        assert p4values.encode_ternary(value, 128) == result


def test_encode_ternary_fail():
    "Test the encode_ternary function."
    data = [
        (1 + 2j, 32),
        ("abc", 0),  # SdnString not supported
    ]

    for value, bitwidth in data:
        with pytest.raises(ValueError):
            p4values.encode_ternary(value, bitwidth)  # type: ignore


def test_decode_ternary_int():
    "Test the decode_ternary function."
    data = [
        (b"\x00", b"\xff", 8, (0, 0xFF), "0x0"),
        (b"\x03", b"\x0f", 4, (3, 0x0F), "0x3"),
        (b"\x01", b"\x01", 32, (1, 1), "0x1/&0x1"),
        (
            b"\xc0\xa8\x01\x01",
            b"\xff\xff\xff\x00",
            32,
            (3232235777, 4294967040),
            "0xc0a80101/24",
        ),
        (
            b"\xc0\xa8\x01\x01",
            b"\x7f\xff\xff\x00",
            32,
            (3232235777, 2147483392),
            "0xc0a80101/&0x7fffff00",
        ),
    ]

    for value, mask, bitwidth, res_tup, res_str in data:
        assert p4values.decode_ternary(value, mask, bitwidth) == res_tup
        assert (
            p4values.decode_ternary(value, mask, bitwidth, DecodeFormat.STRING)
            == res_str
        )


def test_decode_ternary_ipv4():
    "Test the decode_ternary function."
    data = [
        (b"\x01", b"\x01", (IP("0.0.0.1"), IP("0.0.0.1")), "0.0.0.1/&0.0.0.1"),
        (
            b"\xc0\xa8\x01\x01",
            b"\xff\xff\xff\x00",
            (IP("192.168.1.1"), IP("255.255.255.0")),
            "192.168.1.1/24",
        ),
        (
            b"\xc0\xa8\x01\x01",
            b"\xff\xff\xff\xff",
            (IP("192.168.1.1"), IP("255.255.255.255")),
            "192.168.1.1",
        ),
    ]

    for value, mask, res_tup, res_str in data:
        assert p4values.decode_ternary(value, mask, 32, DecodeFormat.ADDRESS) == res_tup
        assert p4values.decode_ternary(value, mask, 32, ADDR_STR) == res_str


def test_decode_ternary_ipv6():
    "Test the decode_ternary function."
    data = [
        (
            b"\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
            b"\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00",
            (IP("2000::"), IP("ffff:ffff:ffff:ffff::")),
            "2000::/64",
        )
    ]

    for value, mask, res_tup, res_str in data:
        assert (
            p4values.decode_ternary(value, mask, 128, DecodeFormat.ADDRESS) == res_tup
        )
        assert p4values.decode_ternary(value, mask, 128, ADDR_STR) == res_str


def test_encode_range_int():
    "Test the encode_range function."
    data = [
        ((1, 2), 32, (b"\x01", b"\x02")),
        ("1...2", 32, (b"\x01", b"\x02")),
    ]

    for value, bitwidth, result in data:
        assert p4values.encode_range(value, bitwidth) == result


def test_encode_range_ipv4():
    "Test the encode_range function."
    data = [
        ((IP("1.2.3.4"), IP("1.2.3.5")), (b"\x01\x02\x03\x04", b"\x01\x02\x03\x05")),
        (("1.2.3.4", "1.2.3.5"), (b"\x01\x02\x03\x04", b"\x01\x02\x03\x05")),
        ("1.2.3.4...1.2.3.5", (b"\x01\x02\x03\x04", b"\x01\x02\x03\x05")),
    ]

    for value, result in data:
        assert p4values.encode_range(value, 32) == result


def test_encode_range_ipv6():
    "Test the encode_range function."
    data = [
        (
            (IP("2000::1"), IP("2000::2")),
            (
                b"\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01",
                b"\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02",
            ),
        ),
        (
            ("2000::1", "2000::2"),
            (
                b"\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01",
                b"\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02",
            ),
        ),
        (
            "2000::1...2000::2",
            (
                b"\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01",
                b"\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02",
            ),
        ),
    ]

    for value, result in data:
        assert p4values.encode_range(value, 128) == result


def test_encode_range_fail():
    "Test the encode_range function."
    data = [
        (1 + 2j, 32),
        ("abc", 0),  # SdnString not supported
    ]

    for value, bitwidth in data:
        with pytest.raises(ValueError):
            p4values.encode_range(value, bitwidth)  # type: ignore


def test_decode_range_int():
    "Test the decode_range function."
    data = [(b"\x01", b"\x02", 32, (1, 2))]

    def _to_str(value: tuple[Any, Any]):
        return f"{value[0]:#x}...{value[1]:#x}"

    for lo, hi, bitwidth, result in data:
        assert p4values.decode_range(lo, hi, bitwidth) == result
        assert p4values.decode_range(lo, hi, bitwidth, DecodeFormat.STRING) == _to_str(
            result
        )


def test_decode_range_ipv4():
    "Test the decode_range function."
    data = [
        (b"\x01\x02\x03\x04", b"\x01\x02\x03\x05", (IP("1.2.3.4"), IP("1.2.3.5"))),
    ]

    def _to_str(value: tuple[Any, Any]):
        return f"{value[0]}...{value[1]}"

    for lo, hi, result in data:
        assert p4values.decode_range(lo, hi, 32, DecodeFormat.ADDRESS) == result
        assert p4values.decode_range(lo, hi, 32, ADDR_STR) == _to_str(result)


def test_decode_range_ipv6():
    "Test the decode_range function."
    data = [
        (
            b"\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01",
            b"\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02",
            (IP("2000::1"), IP("2000::2")),
        ),
    ]

    def _to_str(value: tuple[Any, Any]):
        return f"{value[0]}...{value[1]}"

    for lo, hi, result in data:
        assert p4values.decode_range(lo, hi, 128, DecodeFormat.ADDRESS) == result
        assert p4values.decode_range(lo, hi, 128, ADDR_STR) == _to_str(result)
