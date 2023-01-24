from pathlib import Path

import finsy.pbuf as pbuf
from finsy.proto import p4testgen

TEST_DIR = Path(__file__).parent / "test_data/p4testgen"


def test_p4testgen_testcase_0():
    "Test a p4testgen testcase file."
    path = TEST_DIR / "hello_0.proto.txt"
    testcase = pbuf.from_text(path.read_text(), p4testgen.TestCase)

    assert isinstance(testcase.input_packet.packet, bytes)
    assert len(testcase.input_packet.packet) == 929
    assert testcase.input_packet.port == 255

    for expected in testcase.expected_output_packet:
        assert expected.packet == testcase.input_packet.packet
        assert expected.packet_mask == b"\xff" * 929
        assert expected.port == 255


def test_p4testgen_testcase_13():
    "Test a p4testgen testcase file."
    path = TEST_DIR / "hello_13.proto.txt"
    testcase = pbuf.from_text(path.read_text(), p4testgen.TestCase)

    assert isinstance(testcase.input_packet.packet, bytes)
    assert len(testcase.input_packet.packet) == 8193
    assert testcase.input_packet.port == 0

    assert len(testcase.entities) == 1
    assert pbuf.to_dict(testcase.entities[0]) == {
        "table_entry": {
            "table_id": 44387528,
            "match": [{"field_id": 1, "exact": {"value": "AAAAAA=="}}],
            "action": {
                "action": {
                    "action_id": 29683729,
                    "params": [{"param_id": 1, "value": "AAA="}],
                }
            },
        }
    }
