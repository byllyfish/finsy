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


def test_unicode_path():
    value = "\\x00\\x01\\x02\\x03\\x04\\x05\\x06\\x07\\x08\\t\\n\\x0b\\x0c\\r\\x0e\\x0f\\x10\\x11\\x12\\x13\\x14\\x15\\x16\\x17\\x18\\x19\\x1a\\x1b\\x1c\\x1d\\x1e\\x1f!\"#$%&'()*+,-.0123456789:;<>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ^_`abcdefghijklmnopqrstuvwxyz{|}~\\x7f\\x80\\x81\\x82\\x83\\x84\\x85\\x86\\x87\\x88\\x89\\x8a\\x8b\\x8c\\x8d\\x8e\\x8f\\x90\\x91\\x92\\x93\\x94\\x95\\x96\\x97\\x98\\x99\\x9a\\x9b\\x9c\\x9d\\x9e\\x9f\\xa0\\xa1\\xa2\\xa3\\xa4\\xa5\\xa6\\xa7\\xa8\\xa9\\xaa\\xab\\xac\\xad\\xae\\xaf\\xb0\\xb1\\xb2\\xb3\\xb4\\xb5\\xb6\\xb7\\xb8\\xb9\\xba\\xbb\\xbc\\xbd\\xbe\\xbf\\xc0\\xc1\\xc2\\xc3\\xc4\\xc5\\xc6\\xc7\\xc8\\xc9\\xca\\xcb\\xcc\\xcd\\xce\\xcf\\xd0\\xd1\\xd2\\xd3\\xd4\\xd5\\xd6\\xd7\\xd8\\xd9\\xda\\xdb\\xdc\\xdd\\xde\\xdf\\xe0\\xe1\\xe2\\xe3\\xe4\\xe5\\xe6\\xe7\\xe8\\xe9\\xea\\xeb\\xec\\xed\\xee\\xef\\xf0\\xf1\\xf2\\xf3\\xf4\\xf5\\xf6\\xf7\\xf8\\xf9\\xfa\\xfb\\xfc\\xfd\\xfe\\xff\\u0100\\u0101\\u0102\\u0103"
    expected = "\\u0000\\u0001\\u0002\\u0003\\u0004\\u0005\\u0006\\u0007\\u0008\\u0009\\n\\u000b\\u000c\\r\\u000e\\u000f\\u0010\\u0011\\u0012\\u0013\\u0014\\u0015\\u0016\\u0017\\u0018\\u0019\\u001a\\u001b\\u001c\\u001d\\u001e\\u001f!\"#$%&'()*+,-.0123456789:;<>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ^_`abcdefghijklmnopqrstuvwxyz{|}~\\u007f\\u0080\\u0081\\u0082\\u0083\\u0084\\u0085\\u0086\\u0087\\u0088\\u0089\\u008a\\u008b\\u008c\\u008d\\u008e\\u008f\\u0090\\u0091\\u0092\\u0093\\u0094\\u0095\\u0096\\u0097\\u0098\\u0099\\u009a\\u009b\\u009c\\u009d\\u009e\\u009f\\u00a0\\u00a1\\u00a2\\u00a3\\u00a4\\u00a5\\u00a6\\u00a7\\u00a8\\u00a9\\u00aa\\u00ab\\u00ac\\u00ad\\u00ae\\u00af\\u00b0\\u00b1\\u00b2\\u00b3\\u00b4\\u00b5\\u00b6\\u00b7\\u00b8\\u00b9\\u00ba\\u00bb\\u00bc\\u00bd\\u00be\\u00bf\\u00c0\\u00c1\\u00c2\\u00c3\\u00c4\\u00c5\\u00c6\\u00c7\\u00c8\\u00c9\\u00ca\\u00cb\\u00cc\\u00cd\\u00ce\\u00cf\\u00d0\\u00d1\\u00d2\\u00d3\\u00d4\\u00d5\\u00d6\\u00d7\\u00d8\\u00d9\\u00da\\u00db\\u00dc\\u00dd\\u00de\\u00df\\u00e0\\u00e1\\u00e2\\u00e3\\u00e4\\u00e5\\u00e6\\u00e7\\u00e8\\u00e9\\u00ea\\u00eb\\u00ec\\u00ed\\u00ee\\u00ef\\u00f0\\u00f1\\u00f2\\u00f3\\u00f4\\u00f5\\u00f6\\u00f7\\u00f8\\u00f9\\u00fa\\u00fb\\u00fc\\u00fd\\u00fe\\u00ff\\u0100\\u0101\\u0102\\u0103"

    assert to_str(parse(value)) == expected
    assert to_str(parse(expected)) == expected
