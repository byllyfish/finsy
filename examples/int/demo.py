import asyncio
from pathlib import Path

from int_p4info import *

import finsy as fy

P4SRC = Path(__file__).parent / "p4"

H1_MAC = "00:00:00:00:01:01"
H2_MAC = "00:00:00:00:02:02"
H3_MAC = "00:00:00:00:03:03"
INTC_MAC = "00:00:00:00:09:09"

H1_IP = "10.0.1.1"
H2_IP = "10.0.2.2"
H3_IP = "10.0.3.3"
INTC_IP = "10.0.9.9"

S1_MAC = "f6:00:00:00:00:01"
S2_MAC = "f6:00:00:00:00:02"
S3_MAC = "f6:00:00:00:00:03"

S1_IP = "10.0.0.1"
S2_IP = "10.0.0.2"
S3_IP = "10.0.0.3"

INTC_PORT = 6000


S1 = [
    +tb_activate_source__activate_source(ingress_port=1),
    +tb_int_source__configure_source(
        priority=1,
        srcAddr=H1_IP,
        dstAddr=H2_IP,
        l4_src="0/0",
        l4_dst="0/0",
        max_hop=4,
        hop_metadata_len=10,
        ins_cnt=8,
        ins_mask=0xFF00,
    ),
    +tb_int_source__configure_source(
        priority=1,
        srcAddr="150.254.169.196",
        dstAddr="195.113.172.46",
        l4_src=0x11FF,
        l4_dst=0x4268,
        max_hop=4,
        hop_metadata_len=6,
        ins_cnt=4,
        ins_mask=0xCC00,
    ),
    +tb_int_sink__configure_sink(egress_spec=1, sink_reporting_port=4),
    +fy.P4CloneSessionEntry(1, replicas=(4,)),
    +tb_int_reporting__send_report(
        dp_mac=S1_MAC,
        dp_ip=S1_IP,
        collector_mac=INTC_MAC,
        collector_ip=INTC_IP,
        collector_port=INTC_PORT,
    ),
    +tb_int_transit__configure_transit(switch_id=1, l3_mtu=1500),
    +tb_forward__send_to_port(priority=1, dstAddr="00:10:db:ff:10:02", port=2),
    +tb_forward__send_to_port(priority=10, dstAddr=H2_MAC, port=3),
    +tb_forward__send_to_port(priority=11, dstAddr=H1_MAC, port=1),
]


S2 = [
    +tb_activate_source__activate_source(ingress_port=1),
    +tb_int_sink__configure_sink(egress_spec=1, sink_reporting_port=4),
    +fy.P4CloneSessionEntry(1, replicas=(4,)),
    +tb_int_reporting__send_report(
        dp_mac=S2_MAC,
        dp_ip=S2_IP,
        collector_mac=INTC_MAC,
        collector_ip=INTC_IP,
        collector_port=INTC_PORT,
    ),
    +tb_int_transit__configure_transit(switch_id=2, l3_mtu=1500),
    +tb_forward__send_to_port(
        priority=11,
        dstAddr=H1_MAC,
        port=2,
    ),
    +tb_forward__send_to_port(
        priority=1,
        dstAddr="00:10:db:ff:10:02",
        port=5,
    ),
    +tb_forward__send_to_port(
        priority=10,
        dstAddr=H2_MAC,
        port=1,
    ),
]


S3 = [
    +tb_activate_source__activate_source(ingress_port=1),
    +tb_int_source__configure_source(
        priority=1,
        srcAddr=H3_IP,
        dstAddr=H2_IP,
        l4_src=0x11FF,
        l4_dst=0x22FF,
        max_hop=4,
        hop_metadata_len=2,
        ins_cnt=2,
        ins_mask=0xC0,
    ),
    +tb_int_sink__configure_sink(egress_spec=1, sink_reporting_port=4),
    +fy.P4CloneSessionEntry(1, replicas=(4,)),
    +tb_int_reporting__send_report(
        dp_mac=S3_MAC,
        dp_ip=S3_IP,
        collector_mac=INTC_MAC,
        collector_ip=INTC_IP,
        collector_port=6000,
    ),
    +tb_int_transit__configure_transit(switch_id=3, l3_mtu=1500),
    +tb_forward__send_to_port(
        priority=9,
        dstAddr=H2_MAC,
        port=3,
    ),
    +tb_forward__send_to_port(
        priority=10,
        dstAddr="26:82:e5:03:8f:6e",
        port=5,
    ),
]


async def ready_handler(sw: fy.Switch):
    await sw.write(sw.options.configuration)


async def main():
    opts = fy.SwitchOptions(
        p4info=P4SRC / "int.p4info.txt",
        p4blob=P4SRC / "int.json",
        p4force=True,
        ready_handler=ready_handler,
    )

    switches = [
        fy.Switch("s1", "127.0.0.1:50001", opts(configuration=S1)),
        fy.Switch("s2", "127.0.0.1:50002", opts(configuration=S2)),
        fy.Switch("s3", "127.0.0.1:50003", opts(configuration=S3)),
    ]

    controller = fy.Controller(switches)
    await controller.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
