import asyncio
import logging
from pathlib import Path

import testlib

NGSDN_DIR = Path(__file__).parent.parent / "ngsdn"

DEMONET = NGSDN_DIR / "demonet/run.sh"


async def test_ngsdn(demonet, python):
    "Test the ngsdn/ngsdn example program."

    async with python("-m", "ngsdn").env(PYTHONPATH="..:ngsdn") as demo:
        await asyncio.sleep(2.0)

        # These are IPv6 pings.
        await demonet.send("h1a ping -c 1 h3")
        await demonet.send("h3 ping -c 1 h1a")
        await demonet.send("h1a ping -c 1 h3", expect=" 0% packet loss")

        demo.cancel()


async def test_read_tables(demonet, caplog):
    "Test the state of the tables after the demo finishes."

    expected_switch_states = {
        "127.0.0.1:50001": {
            "acl_table ingress_port=* dst_addr=* src_addr=* ether_type=0x806/&0xffff ip_proto=* icmp_type=* l4_src_port=* l4_dst_port=* clone_to_cpu()",
            "acl_table ingress_port=* dst_addr=* src_addr=* ether_type=0x86dd/&0xffff ip_proto=0x3a/&0xff icmp_type=0x87/&0xff l4_src_port=* l4_dst_port=* clone_to_cpu()",
            "acl_table ingress_port=* dst_addr=* src_addr=* ether_type=0x86dd/&0xffff ip_proto=0x3a/&0xff icmp_type=0x88/&0xff l4_src_port=* l4_dst_port=* clone_to_cpu()",
            "acl_table ingress_port=* dst_addr=* src_addr=* ether_type=0x88cc/&0xffff ip_proto=* icmp_type=* l4_src_port=* l4_dst_port=* send_to_cpu()",
            "l2_exact_table dst_addr=0x1a set_egress_port(port_num=0x3)",
            "l2_exact_table dst_addr=0xbb00000001 set_egress_port(port_num=0x1)",
            "l2_exact_table dst_addr=0xbb00000002 set_egress_port(port_num=0x2)",
            "l2_ternary_table dst_addr=0x333300000000/&0xffff00000000 set_multicast_group(gid=0x63)",
            "l2_ternary_table dst_addr=0xffffffffffff/&0xffffffffffff set_multicast_group(gid=0x63)",
            "my_station_table dst_addr=0xaa00000001 NoAction()",
            "ndp_reply_table target_ipv6_addr=0x200100010001000000000000000000ff ndp_ns_to_na(target_mac=0xaa00000001)",
            "ndp_reply_table target_ipv6_addr=0x200100010002000000000000000000ff ndp_ns_to_na(target_mac=0xaa00000001)",
            "routing_v6_table dst_addr=0x2001000100010000000000000000000a/128 1*set_next_hop(dmac=0x1a)",
            "routing_v6_table dst_addr=0x20010002000300000000000000000000/64 1*set_next_hop(dmac=0xbb00000001) 1*set_next_hop(dmac=0xbb00000002)",
            "routing_v6_table dst_addr=0x20010002000400000000000000000000/64 1*set_next_hop(dmac=0xbb00000001) 1*set_next_hop(dmac=0xbb00000002)",
            "routing_v6_table dst_addr=0x30201000200000000000000000000/128 1*set_next_hop(dmac=0xbb00000001)",
            "routing_v6_table dst_addr=0x30202000200000000000000000000/128 1*set_next_hop(dmac=0xbb00000002)",
            "srv6_my_sid dst_addr=0x30101000200000000000000000000/128 srv6_end()",
        },
        "127.0.0.1:50002": {
            "acl_table ingress_port=* dst_addr=* src_addr=* ether_type=0x806/&0xffff ip_proto=* icmp_type=* l4_src_port=* l4_dst_port=* clone_to_cpu()",
            "acl_table ingress_port=* dst_addr=* src_addr=* ether_type=0x86dd/&0xffff ip_proto=0x3a/&0xff icmp_type=0x87/&0xff l4_src_port=* l4_dst_port=* clone_to_cpu()",
            "acl_table ingress_port=* dst_addr=* src_addr=* ether_type=0x86dd/&0xffff ip_proto=0x3a/&0xff icmp_type=0x88/&0xff l4_src_port=* l4_dst_port=* clone_to_cpu()",
            "acl_table ingress_port=* dst_addr=* src_addr=* ether_type=0x88cc/&0xffff ip_proto=* icmp_type=* l4_src_port=* l4_dst_port=* send_to_cpu()",
            "l2_exact_table dst_addr=0x30 set_egress_port(port_num=0x3)",
            "l2_exact_table dst_addr=0xbb00000001 set_egress_port(port_num=0x1)",
            "l2_exact_table dst_addr=0xbb00000002 set_egress_port(port_num=0x2)",
            "l2_ternary_table dst_addr=0x333300000000/&0xffff00000000 set_multicast_group(gid=0x63)",
            "l2_ternary_table dst_addr=0xffffffffffff/&0xffffffffffff set_multicast_group(gid=0x63)",
            "my_station_table dst_addr=0xaa00000002 NoAction()",
            "ndp_reply_table target_ipv6_addr=0x200100020003000000000000000000ff ndp_ns_to_na(target_mac=0xaa00000002)",
            "ndp_reply_table target_ipv6_addr=0x200100020004000000000000000000ff ndp_ns_to_na(target_mac=0xaa00000002)",
            "routing_v6_table dst_addr=0x20010001000100000000000000000000/64 1*set_next_hop(dmac=0xbb00000001) 1*set_next_hop(dmac=0xbb00000002)",
            "routing_v6_table dst_addr=0x20010001000200000000000000000000/64 1*set_next_hop(dmac=0xbb00000001) 1*set_next_hop(dmac=0xbb00000002)",
            "routing_v6_table dst_addr=0x20010002000300000000000000000001/128 1*set_next_hop(dmac=0x30)",
            "routing_v6_table dst_addr=0x30201000200000000000000000000/128 1*set_next_hop(dmac=0xbb00000001)",
            "routing_v6_table dst_addr=0x30202000200000000000000000000/128 1*set_next_hop(dmac=0xbb00000002)",
            "srv6_my_sid dst_addr=0x30102000200000000000000000000/128 srv6_end()",
        },
        "127.0.0.1:50003": {
            "acl_table ingress_port=* dst_addr=* src_addr=* ether_type=0x88cc/&0xffff ip_proto=* icmp_type=* l4_src_port=* l4_dst_port=* send_to_cpu()",
            "l2_exact_table dst_addr=0xaa00000001 set_egress_port(port_num=0x1)",
            "l2_exact_table dst_addr=0xaa00000002 set_egress_port(port_num=0x2)",
            "my_station_table dst_addr=0xbb00000001 NoAction()",
            "routing_v6_table dst_addr=0x20010001000100000000000000000000/64 1*set_next_hop(dmac=0xaa00000001)",
            "routing_v6_table dst_addr=0x20010001000200000000000000000000/64 1*set_next_hop(dmac=0xaa00000001)",
            "routing_v6_table dst_addr=0x20010002000300000000000000000000/64 1*set_next_hop(dmac=0xaa00000002)",
            "routing_v6_table dst_addr=0x20010002000400000000000000000000/64 1*set_next_hop(dmac=0xaa00000002)",
            "routing_v6_table dst_addr=0x30101000200000000000000000000/128 1*set_next_hop(dmac=0xaa00000001)",
            "routing_v6_table dst_addr=0x30102000200000000000000000000/128 1*set_next_hop(dmac=0xaa00000002)",
            "srv6_my_sid dst_addr=0x30201000200000000000000000000/128 srv6_end()",
        },
        "127.0.0.1:50004": {
            "acl_table ingress_port=* dst_addr=* src_addr=* ether_type=0x88cc/&0xffff ip_proto=* icmp_type=* l4_src_port=* l4_dst_port=* send_to_cpu()",
            "l2_exact_table dst_addr=0xaa00000001 set_egress_port(port_num=0x1)",
            "l2_exact_table dst_addr=0xaa00000002 set_egress_port(port_num=0x2)",
            "my_station_table dst_addr=0xbb00000002 NoAction()",
            "routing_v6_table dst_addr=0x20010001000100000000000000000000/64 1*set_next_hop(dmac=0xaa00000001)",
            "routing_v6_table dst_addr=0x20010001000200000000000000000000/64 1*set_next_hop(dmac=0xaa00000001)",
            "routing_v6_table dst_addr=0x20010002000300000000000000000000/64 1*set_next_hop(dmac=0xaa00000002)",
            "routing_v6_table dst_addr=0x20010002000400000000000000000000/64 1*set_next_hop(dmac=0xaa00000002)",
            "routing_v6_table dst_addr=0x30101000200000000000000000000/128 1*set_next_hop(dmac=0xaa00000001)",
            "routing_v6_table dst_addr=0x30102000200000000000000000000/128 1*set_next_hop(dmac=0xaa00000002)",
            "srv6_my_sid dst_addr=0x30202000200000000000000000000/128 srv6_end()",
        },
    }

    for target, expected_state in expected_switch_states.items():
        actual_state = await testlib.read_p4_tables(target)
        assert actual_state == expected_state
