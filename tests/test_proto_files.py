from pathlib import Path

import finsy.pbuf as pbuf
from finsy.proto import p4testgen

TEST_DIR = Path(__file__).parent / "test_data/p4testgen"


def test_p4testgen_testcase():
    "Test a p4testgen testcase file."
    path = TEST_DIR / "hello_0.proto.txt"
    testcase = pbuf.from_text(path.read_text(), p4testgen.TestCase)

    assert isinstance(testcase.input_packet.packet, bytes)
    assert len(testcase.input_packet.packet) == 929
    assert testcase.input_packet.port == b"255"

    for expected in testcase.expected_output_packet:
        assert expected.packet == testcase.input_packet.packet
        assert expected.packet_mask == b"\xff" * 929
        assert expected.port == b"255"
