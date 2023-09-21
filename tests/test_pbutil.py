from pathlib import Path

import pytest

from finsy import pbutil
from finsy.p4schema import P4Schema
from finsy.proto import p4i, p4r

_P4INFO = p4i.P4Info(
    pkg_info=p4i.PkgInfo(
        arch="v1model",
    ),
)

P4INFO_TEST_DIR = Path(__file__).parent / "test_data/p4info"

_P4WRITE_REQ = p4r.WriteRequest(
    updates=[
        p4r.Update(
            type=p4r.Update.DELETE,
            entity=p4r.Entity(table_entry=p4r.TableEntry(table_id=1)),
        ),
        p4r.Update(
            type=p4r.Update.DELETE,
            entity=p4r.Entity(table_entry=p4r.TableEntry(table_id=2)),
        ),
    ]
)


def test_from_text_with_text_input1():
    "Test from_text() with text input."
    data = str(_P4INFO)
    msg = pbutil.from_text(data, p4i.P4Info)
    assert msg == _P4INFO


def test_from_text_with_text_input2():
    "Test from_text() with text input."
    data = str(_P4WRITE_REQ)
    msg = pbutil.from_text(data, p4r.WriteRequest)
    assert msg == _P4WRITE_REQ


def test_from_text_with_json_input1():
    "Test from_text() with JSON input."
    data = pbutil.to_json(_P4INFO)
    msg = pbutil.from_text(data, p4i.P4Info)
    assert msg == _P4INFO


def test_from_text_with_json_input2():
    "Test from_text() with JSON input."
    data = pbutil.to_json(_P4WRITE_REQ)
    msg = pbutil.from_text(data, p4r.WriteRequest)
    assert msg == _P4WRITE_REQ


def test_from_dict1():
    data = pbutil.to_dict(_P4INFO)
    msg = pbutil.from_dict(data, p4i.P4Info)
    assert msg == _P4INFO


def test_from_dict2():
    data = pbutil.to_dict(_P4WRITE_REQ)
    msg = pbutil.from_dict(data, p4r.WriteRequest)
    assert msg == _P4WRITE_REQ


def test_to_json1():
    data = pbutil.to_json(_P4INFO)
    assert data == '{\n  "pkg_info": {\n    "arch": "v1model"\n  }\n}'


def test_to_json2():
    data = pbutil.to_json(_P4WRITE_REQ)
    assert (
        data
        == '{\n  "updates": [\n    {\n      "type": "DELETE",\n      "entity": {\n        "table_entry": {\n          "table_id": 1\n        }\n      }\n    },\n    {\n      "type": "DELETE",\n      "entity": {\n        "table_entry": {\n          "table_id": 2\n        }\n      }\n    }\n  ]\n}'
    )


def test_to_text1():
    data = pbutil.to_text(_P4INFO)
    assert data == 'pkg_info { arch: "v1model" }'


def test_to_text2():
    schema = P4Schema(P4INFO_TEST_DIR / "basic.p4.p4info.txt")
    data = pbutil.to_text(schema.get_pipeline_config(), custom_format=True)
    assert data == "\U0001f4e6p4cookie=0x541828e970ff3d19"


def test_to_text3():
    data = pbutil.to_text(_P4WRITE_REQ)
    assert (
        data
        == "updates { type: DELETE entity { table_entry { table_id: 1 } } } updates { type: DELETE entity { table_entry { table_id: 2 } } }"
    )


def test_to_dict():
    data = pbutil.to_dict(_P4INFO)
    assert data == {"pkg_info": {"arch": "v1model"}}


def test_from_any():
    "Test the `from_any` function."
    any_obj = pbutil.PBAny()
    any_obj.Pack(_P4INFO)

    assert pbutil.to_dict(any_obj) == {
        "@type": "type.googleapis.com/p4.config.v1.P4Info",
        "pkg_info": {"arch": "v1model"},
    }

    obj = pbutil.from_any(any_obj, p4i.P4Info)
    assert pbutil.to_dict(obj) == {"pkg_info": {"arch": "v1model"}}

    with pytest.raises(ValueError, match="Not a Extern"):
        pbutil.from_any(any_obj, p4i.Extern)


def test_to_any():
    "Test the `to_any` function."
    any_obj = pbutil.PBAny()
    any_obj.Pack(_P4INFO)
    assert pbutil.to_any(_P4INFO) == any_obj


def test_log_annotate():
    "Test the log_annotate() function (with invalid input)."
    schema = P4Schema(P4INFO_TEST_DIR / "basic.p4.p4info.txt")

    # digest_id doesn't exist
    text = "digest_id: foo\n"
    assert pbutil.log_annotate(text, schema) == text

    # digest_id doesn't exist
    text = "digest_id: 123\n"
    assert pbutil.log_annotate(text, schema) == text

    # invalid escape value
    text = '  value: "\\xgg"\n'
    assert pbutil.log_annotate(text, schema) == text

    # missing quotes
    text = "  value: 123\n"
    assert pbutil.log_annotate(text, schema) == text
