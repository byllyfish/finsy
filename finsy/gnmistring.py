"Implements string conversion for `gnmi.Path`."

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

# pyright/strict and parsy don't mix well.
#   pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
#   pyright: reportUnknownParameterType=false, reportUnknownVariableType=false
#   pyright: reportFunctionMemberAccess=false, reportUnknownLambdaType=false

import re

import parsy as pa  # pyright: ignore[reportMissingTypeStubs]

from finsy.proto import gnmi

#################################
# Parser Combinator Definitions #
#################################

_SLASH = pa.string("/")
_LBRACK = pa.string("[")
_RBRACK = pa.string("]")
_EQUALS = pa.string("=")

__ID1 = pa.regex(r"[^\s\\/\[=\]]+").desc("_ID1")  # char+ no SPACE \ / [ ] =
# N.B. '[' is not allowed in a key unless it is escaped. This is required by
# unit tests, but this restriction could be removed in the future.
__KEY = pa.regex(r"[^\s\\\]=\[]+").desc("_KEY")  # char+ no SPACE \ [ ] =
__VAL = pa.regex(r"[^\\\]]+").desc("_VAL")  # char+ no \ ]
__ESC = pa.string("\\") >> (  # backslash escape sequence
    pa.char_from("\\/[]=")
    | pa.string("n").result("\n")
    | pa.string("r").result("\r")
    | pa.string("t").result("\t")
    | pa.regex(r"x[0-9a-fA-F]{2}").map(lambda s: chr(int(s[1:], 16)))
    | pa.regex(r"u[0-9a-fA-F]{4}").map(lambda s: chr(int(s[1:], 16)))
    | pa.regex(r"U[0-9a-fA-F]{8}").map(lambda s: chr(int(s[1:], 16)))
)

_IDENT = (__ID1 | __ESC).at_least(1).concat().desc("_IDENT")
_IDKEY = (__KEY | __ESC).at_least(1).concat().desc("_IDKEY")
_IDVAL = (__VAL | __ESC).at_least(1).concat().desc("_IDVAL")


@pa.generate
def _keyval():
    "Parse `[ IDKEY = IDVAL ]`"
    yield _LBRACK
    key = yield _IDKEY
    yield _EQUALS
    value = yield _IDVAL
    yield _RBRACK
    return key, value


@pa.generate
def _elem():
    "Parse `IDENT KEYVAL*`"
    ident = yield _IDENT
    kvs = yield _keyval.many()

    keys = {}
    for k, v in kvs:
        if k in keys:
            raise ValueError(f"parse failed: duplicate key {k!r}")
        keys[k] = v
    return ident, keys


@pa.generate
def _elems():
    """Parse zero or more `_elem` separated by `/`.
    Ignore a single slash at the beginning or end.
    """
    yield _SLASH.optional()
    elems = yield _elem.sep_by(_SLASH)
    yield _SLASH.optional()
    return elems


################################################################################

# This module provides two functions: `parse` and `to_str`.
#
# Example:
#
# ```
# path = gnmistring.parse("interfaces/interface[name=eth1]/state")
# ```
#
# This module does NOT allow the `origin` or `target` prefix properties to be
# specified in the string. Set these in `GNMIPath`.
#
# FIXME: This module does not support Unicode surrogate pairs.
#
# Reference:
# https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-path-strings.md


def parse(value: str) -> gnmi.Path:
    "Parse a string as a `gnmi.Path`."
    if value in ("/", ""):
        return gnmi.Path()

    try:
        elems = _elems.parse(value)
    except pa.ParseError as ex:
        # Map ParseError to ValueError for convenience.
        raise ValueError(f"parse failed: {ex} (value={value!r})") from ex

    result = gnmi.Path()
    for elem, key in elems:
        result.elem.add(name=elem, key=key)

    return result


def to_str(path: gnmi.Path) -> str:
    "Encode a `gnmi.Path` as a string."
    if not path.elem:
        return "/"

    return "/".join(_elem_str(elem) for elem in path.elem)


def _elem_str(elem: gnmi.PathElem) -> str:
    """Encode a `gnmi.PathElem` as a string."""
    name = _escape(elem.name, "[]/=", True)
    keyvals = [
        f"[{_escape(key,'[]=', True)}={_escape(val, ']', False)}]"
        for key, val in sorted(elem.key.items())
    ]

    return "".join([name, *keyvals])


_REPLACE_ESCAPES = re.compile(rb"\\x[0-9a-fA-F]{2}|\\t")


def _escape(value: str, chars: str, esc_space: bool) -> str:
    """Backslash escape the specified characters in value. If `esc_space` is
    True, we also escape spaces."""

    def _replace(m: re.Match[bytes]) -> bytes:
        s = m.group(0)
        if s[0:2] == rb"\t":
            return rb"\u0009"
        assert s[0:2] == rb"\x"
        return rb"\u00" + s[2:]

    # Canonical: Translate \xHH and \t escapes to \uHHHH.
    data = value.encode("unicode-escape")
    data = _REPLACE_ESCAPES.sub(_replace, data)

    table = {ord(char): f"\\{char}" for char in chars}
    if esc_space:  # space is escaped in ID and KEY (but not in VAL).
        table[0x20] = r"\u0020"

    return data.decode("ascii").translate(table)
