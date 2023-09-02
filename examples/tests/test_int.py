import asyncio
from pathlib import Path

import testlib

INT_DIR = Path(__file__).parents[1] / "int"

DEMONET = INT_DIR / "net/run.py"


async def test_demo(demonet, python):
    "Test the int/demo example program."
    async with python(INT_DIR / "demo") as demo:
        await asyncio.sleep(0.25)
        await demonet.send("h1 echo 'abc' | socat - udp:192.168.0.48:5555")
        await asyncio.sleep(1.0)
        demo.cancel()


async def test_read_tables(demonet):
    "Test the state of the tables after the demo finishes."
    expected_switch_states = {
        "127.0.0.1:50001": {
            "tb_activate_source ingress_port=0x1 activate_source()",
            "tb_activate_source NoAction()",
            "tb_int_source 0x1 srcAddr=0xa000101 dstAddr=0xa000202 l4_src=* l4_dst=* configure_source(max_hop=0x4, hop_metadata_len=0xa, ins_cnt=0x8, ins_mask=0xff00)",
            "tb_int_source NoAction()",
            "tb_forward 0xb dstAddr=0x101 send_to_port(port=0x1)",
            "tb_forward 0xa dstAddr=0x202 send_to_port(port=0x3)",
            "tb_forward NoAction()",
            "tb_port_forward NoAction()",
            "tb_int_sink egress_spec=0x1 configure_sink(sink_reporting_port=0x4)",
            "tb_int_sink NoAction()",
            "tb_int_reporting send_report(dp_mac=0xf60000000001, dp_ip=0xa000001, collector_mac=0x909, collector_ip=0xa000909, collector_port=0x1770)",
            "tb_int_reporting NoAction()",
            "tb_int_transit NoAction()",
            "tb_int_transit configure_transit(switch_id=0x1, l3_mtu=0x5dc)",
            "/clone/0x1 class_of_service=0 4",
        },
        "127.0.0.1:50002": {
            "tb_int_transit configure_transit(switch_id=0x2, l3_mtu=0x5dc)",
            "tb_int_transit NoAction()",
            "tb_port_forward NoAction()",
            "tb_int_source NoAction()",
            "tb_int_sink NoAction()",
            "tb_activate_source ingress_port=0x1 activate_source()",
            "tb_forward NoAction()",
            "tb_int_reporting NoAction()",
            "tb_activate_source NoAction()",
            "tb_forward 0xa dstAddr=0x202 send_to_port(port=0x1)",
            "tb_int_reporting send_report(dp_mac=0xf60000000002, dp_ip=0xa000002, collector_mac=0x909, collector_ip=0xa000909, collector_port=0x1770)",
            "tb_int_sink egress_spec=0x1 configure_sink(sink_reporting_port=0x4)",
            "tb_forward 0xb dstAddr=0x101 send_to_port(port=0x2)",
            "/clone/0x1 class_of_service=0 4",
        },
        "127.0.0.1:50003": {
            "tb_activate_source NoAction()",
            "tb_int_sink egress_spec=0x1 configure_sink(sink_reporting_port=0x4)",
            "tb_int_reporting send_report(dp_mac=0xf60000000003, dp_ip=0xa000003, collector_mac=0x909, collector_ip=0xa000909, collector_port=0x1770)",
            "tb_int_source NoAction()",
            "tb_int_source 0x1 srcAddr=0xa000303 dstAddr=0xa000202 l4_src=0x11ff l4_dst=0x22ff configure_source(max_hop=0x4, hop_metadata_len=0x2, ins_cnt=0x2, ins_mask=0xc0)",
            "tb_activate_source ingress_port=0x1 activate_source()",
            "tb_int_transit configure_transit(switch_id=0x3, l3_mtu=0x5dc)",
            "tb_forward 0x9 dstAddr=0x202 send_to_port(port=0x3)",
            "tb_int_transit NoAction()",
            "tb_int_reporting NoAction()",
            "tb_port_forward NoAction()",
            "tb_int_sink NoAction()",
            "tb_forward NoAction()",
            "/clone/0x1 class_of_service=0 4",
        },
    }

    for target, expected_state in expected_switch_states.items():
        actual_state = await testlib.read_p4_tables(target, skip_const=True)
        assert actual_state == expected_state, f"{target} failed!"
