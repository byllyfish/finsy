import re

import pytest
from finsy import pbuf
from finsy.gnmistring import parse, to_str

# Test cases from https://github.com/karimra/gnmic/blob/main/utils/path_test.go
# IMPORTANT! My code does NOT support "origin:/" syntax. Also, where tests
# conflict with behavior of pathstrings_test.go from openconfig, we use *that*
# behavior.

_VALID_PATHS1 = {
    "": {},
    "/": {},
    "e": {
        "elem": [
            {"name": "e"},
        ]
    },
    "/e": {
        "elem": [
            {"name": "e"},
        ]
    },
    "/e1/e2": {
        "elem": [
            {"name": "e1"},
            {"name": "e2"},
        ]
    },
    "/e1/e2[k=v]": {
        "elem": [
            {"name": "e1"},
            {"key": {"k": "v"}, "name": "e2"},
        ]
    },
    "/e1/e2[k1=v1][k2=v2]": {
        "elem": [
            {"name": "e1"},
            {"key": {"k1": "v1", "k2": "v2"}, "name": "e2"},
        ]
    },
    # Origin not supported!
    "origin:/e1/e2": {
        "elem": [
            {"name": "origin:"},
            {"name": "e1"},
            {"name": "e2"},
        ]
    },
    "origin:": {
        "elem": [
            {"name": "origin:"},
        ]
    },
    "origin:/": {
        "elem": [
            {"name": "origin:"},
        ]
    },
    ":": {
        "elem": [
            {"name": ":"},
        ]
    },
    ":/": {
        "elem": [
            {"name": ":"},
        ]
    },
    "origin:/e1/e2[k=v]": {
        "elem": [
            {"name": "origin:"},
            {"name": "e1"},
            {"key": {"k": "v"}, "name": "e2"},
        ]
    },
    "origin:/e1[name=object]/e2[addr=1.1.1.1/32]": {
        "elem": [
            {"name": "origin:"},
            {"key": {"name": "object"}, "name": "e1"},
            {"key": {"addr": "1.1.1.1/32"}, "name": "e2"},
        ]
    },
    "origin:/e1:e1[k=1.1.1.1/32]/e2[k1=v2]": {
        "elem": [
            {"name": "origin:"},
            {"key": {"k": "1.1.1.1/32"}, "name": "e1:e1"},
            {"key": {"k1": "v2"}, "name": "e2"},
        ]
    },
    "origin:/e1:e1[k=1.1.1.1/32]/e2:e3[k1=v2]": {
        "elem": [
            {"name": "origin:"},
            {"key": {"k": "1.1.1.1/32"}, "name": "e1:e1"},
            {"key": {"k1": "v2"}, "name": "e2:e3"},
        ]
    },
    r"/e1\[/e2[k=v]": {
        "elem": [
            {"name": "e1["},
            {"key": {"k": "v"}, "name": "e2"},
        ]
    },
    r"/e1\]/e2[k=v]": {
        "elem": [
            {"name": "e1]"},
            {"key": {"k": "v"}, "name": "e2"},
        ]
    },
    "e1:e2/e3[k=v]": {
        "elem": [
            {"name": "e1:e2"},
            {"key": {"k": "v"}, "name": "e3"},
        ]
    },
    "/e1/e2[k=v:1]": {
        "elem": [
            {"name": "e1"},
            {"key": {"k": "v:1"}, "name": "e2"},
        ]
    },
    "e1/e2:e3[k=v:1]": {
        "elem": [
            {"name": "e1"},
            {"key": {"k": "v:1"}, "name": "e2:e3"},
        ]
    },
    "origin:/e1/e2[k=v:1]": {
        "elem": [
            {"name": "origin:"},
            {"name": "e1"},
            {"key": {"k": "v:1"}, "name": "e2"},
        ]
    },
    "origin:/e1/e2[k=v a:1]": {
        "elem": [
            {"name": "origin:"},
            {"name": "e1"},
            {"key": {"k": "v a:1"}, "name": "e2"},
        ]
    },
    'origin:/e1/e2[k="v a:1"]': {
        "elem": [
            {"name": "origin:"},
            {"name": "e1"},
            {"key": {"k": '"v a:1"'}, "name": "e2"},
        ]
    },
}

_INVALID_PATHS1 = [
    "/e1/e2[k=v",
    "/e1/e2k=v]",
    "/e1/e2[k]",
    "/e1/e2]",
    "/e1/e2[k[=v]",
]


# These tests are from "TestPathToString" in:
# https://github.com/openconfig/ygot/blob/master/ygot/pathstrings_test.go

_VALID_PATHS2 = {
    "/a/b/c/d": {
        "elem": [
            {"name": "a"},
            {"name": "b"},
            {"name": "c"},
            {"name": "d"},
        ]
    },
    "/a/b[c=d]/e": {
        "elem": [
            {"name": "a"},
            {"key": {"c": "d"}, "name": "b"},
            {"name": "e"},
        ]
    },
    "/a/b[c=d][e=f]/g": {
        "elem": [
            {"name": "a"},
            {"key": {"c": "d", "e": "f"}, "name": "b"},
            {"name": "g"},
        ],
    },
    r"/interfaces/interface[name=Ethernet1/2/3]": {
        "elem": [
            {"name": "interfaces"},
            {"key": {"name": "Ethernet1/2/3"}, "name": "interface"},
        ]
    },
    (
        r"/interfaces/interface[name=Ethernet\=bar]",
        r"/interfaces/interface[name=Ethernet=bar]",
    ): {
        "elem": [
            {"name": "interfaces"},
            {"key": {"name": "Ethernet=bar"}, "name": "interface"},
        ]
    },
    r"/interfaces/interface[name=[foo]/state": {
        "elem": [
            {"name": "interfaces"},
            {"key": {"name": "[foo"}, "name": "interface"},
            {"name": "state"},
        ]
    },
    r"/interfaces/interface[name=[\\\]]": {
        "elem": [
            {"name": "interfaces"},
            {"key": {"name": "[\\]"}, "name": "interface"},
        ]
    },
    (
        r"/interfaces/interface[name=\/foo]/state",
        r"/interfaces/interface[name=/foo]/state",
    ): {
        "elem": [
            {"name": "interfaces"},
            {"key": {"name": "/foo"}, "name": "interface"},
            {"name": "state"},
        ]
    },
    r"/interfaces/inter\/face[name=foo]": {
        "elem": [
            {"name": "interfaces"},
            {"key": {"name": "foo"}, "name": "inter/face"},
        ]
    },
    (r"/interfaces/interface[name=foo\/bar]", r"/interfaces/interface[name=foo/bar]"): {
        "elem": [
            {"name": "interfaces"},
            {"key": {"name": "foo/bar"}, "name": "interface"},
        ]
    },
    r"/interfaces/interface/*/state": {
        "elem": [
            {"name": "interfaces"},
            {"name": "interface"},
            {"name": "*"},
            {"name": "state"},
        ]
    },
    r"/interfaces/.../state": {
        "elem": [
            {"name": "interfaces"},
            {"name": "..."},
            {"name": "state"},
        ]
    },
    r"/foo/bar\\\/baz/hat": {
        "elem": [
            {"name": "foo"},
            {"name": "bar\\/baz"},
            {"name": "hat"},
        ]
    },
    r"/foo/bar[baz\\foo=hat]": {
        "elem": [
            {"name": "foo"},
            {"key": {"baz\\foo": "hat"}, "name": "bar"},
        ]
    },
    r"/foo/bar[baz==bat]": {
        "elem": [
            {"name": "foo"},
            {"key": {"baz": "=bat"}, "name": "bar"},
        ]
    },
    r"/foo/bar[baz=\]bat]": {
        "elem": [
            {"name": "foo"},
            {"key": {"baz": "]bat"}, "name": "bar"},
        ]
    },
    r"../foo/bar": {
        "elem": [
            {"name": ".."},
            {"name": "foo"},
            {"name": "bar"},
        ]
    },
    r"": {},
    r"/": {},
    r"/foo/bar/": {
        "elem": [
            {"name": "foo"},
            {"name": "bar"},
        ]
    },
    r"foo[bar= baz]": {
        "elem": [
            {"key": {"bar": " baz"}, "name": "foo"},
        ]
    },
    r"neighbors/neighbor[neighbor-address=192.0.2.1]/config/neighbor-address": {
        "elem": [
            {"name": "neighbors"},
            {"key": {"neighbor-address": "192.0.2.1"}, "name": "neighbor"},
            {"name": "config"},
            {"name": "neighbor-address"},
        ]
    },
}


_INVALID_PATHS2 = [
    "/a/b[cd]/e",
    "/foo/bar[baz=]bat]",
    "/foo/bar[baz=bat]hat",
    "/foo/bar[baz=]/hat",
    "/foo/bar[[bar=baz]",
    "/foo/bar]",
    "foo[bar =baz]",
    "foo bar/baz",
    r"\ud83d\ude4f",  # surrogate pairs not supported...
]

# Test Unicode escapes.

_VALID_PATHS3 = {
    (r"/abc\xb7def", r"/abc\u00b7def"): {
        "elem": [
            {"name": "abc\xB7def"},
        ]
    },
    r"/abc\u0123def": {
        "elem": [
            {"name": "abc\u0123def"},
        ]
    },
    (r"abc\n\r\t", r"abc\n\r\u0009"): {
        "elem": [
            {"name": "abc\n\r\t"},
        ]
    },
    r"\U0001d11e": {
        "elem": [
            {"name": "\U0001D11E"},
        ]
    },
}

# Test that canonical path strings are sorted.
_CANONICAL_PATHS = {
    "a[d=1][c=2]/b[z=3][y=4]": "a[c=2][d=1]/b[y=4][z=3]",
}


def _test_parse(value, expected):
    # If value is a tuple, unpack it.
    if isinstance(value, tuple):
        value, roundtrip = value
    else:
        roundtrip = value

    # Parse string value and compare it to expected `gnmi.Path` representaion.
    result = parse(value)
    assert pbuf.to_dict(result) == expected

    # Test roundtrip back to canonical string value.
    if roundtrip in ("", "/"):
        roundtrip = "/"
    else:
        roundtrip = roundtrip.strip("/")
    assert to_str(result) == roundtrip

    # Parse canonical value if different.
    if roundtrip != value:
        result = parse(roundtrip)
        assert pbuf.to_dict(result) == expected


@pytest.mark.parametrize(["value", "expected"], _VALID_PATHS1.items())
def test_valid_paths1(value, expected):
    _test_parse(value, expected)


@pytest.mark.parametrize(["value", "expected"], _VALID_PATHS2.items())
def test_valid_paths2(value, expected):
    _test_parse(value, expected)


@pytest.mark.parametrize(["value", "expected"], _VALID_PATHS3.items())
def test_valid_paths3(value, expected):
    _test_parse(value, expected)


@pytest.mark.parametrize("value", _INVALID_PATHS1)
def test_invalid_paths1(value):
    with pytest.raises(ValueError, match="parse failed"):
        parse(value)


@pytest.mark.parametrize("value", _INVALID_PATHS2)
def test_invalid_paths2(value):
    with pytest.raises(ValueError, match="parse failed|surrogates not allowed"):
        parse(value)


@pytest.mark.parametrize(["value", "expected"], _CANONICAL_PATHS.items())
def test_canonical_paths(value, expected):
    assert to_str(parse(value)) == expected


def test_unicode_roundtrip():
    "Test how Unicode characters are handled in parse/to_str."

    # Produce a long unicode escaped string:
    #  r"\x00\x01\x02\x03...\\u0101\\u0102\\u0103"
    # This string also tests input with \t, \n, \r escapes.
    # The string omits space, /, =, \, [ and ].

    omit = {ord(ch) for ch in r" /=[\]"}
    value = "".join(chr(i) for i in range(260) if i not in omit)
    value = value.encode("unicode_escape").decode("ascii")

    # Produce the expected result by converting \x escapes into \u escapes and
    # replacing \t with "\u0009".

    expected = re.sub(r"\\x([0-9a-f]{2})", r"\\u00\1", value)
    expected = expected.replace(r"\t", r"\u0009")

    assert to_str(parse(value)) == expected
    assert to_str(parse(expected)) == expected
