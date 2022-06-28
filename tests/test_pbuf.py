from pathlib import Path

import pytest
from finsy import pbuf
from finsy.p4schema import P4Schema
from finsy.proto import p4i, p4r

_P4INFO = p4i.P4Info(
    pkg_info=p4i.PkgInfo(
        arch="v1model",
    ),
)

P4INFO_TEST_DIR = Path(__file__).parent / "test_data/p4info"


def test_from_text_with_text_input():
    "Test from_text() with text input."
    data = str(_P4INFO)
    msg = pbuf.from_text(data, p4i.P4Info)
    assert msg == _P4INFO


def test_from_text_with_json_input():
    "Test from_text() with JSON input."
    data = pbuf.to_json(_P4INFO)
    msg = pbuf.from_text(data, p4i.P4Info)
    assert msg == _P4INFO


def test_from_dict():
    data = pbuf.to_dict(_P4INFO)
    msg = pbuf.from_dict(data, p4i.P4Info)
    assert msg == _P4INFO


def test_to_json():
    data = pbuf.to_json(_P4INFO)
    assert data == '{\n  "pkg_info": {\n    "arch": "v1model"\n  }\n}'


def test_to_text1():
    data = pbuf.to_text(_P4INFO)
    assert data == 'pkg_info { arch: "v1model" }'


def test_to_text2():
    schema = P4Schema(P4INFO_TEST_DIR / "basic.p4.p4info.txt")
    data = pbuf.to_text(schema.get_pipeline_config(), custom_format=True)
    assert data == "\U0001f4e6[p4cookie=0x6bbd99ee361bba5a]"


def test_to_dict():
    data = pbuf.to_dict(_P4INFO)
    assert data == {"pkg_info": {"arch": "v1model"}}
