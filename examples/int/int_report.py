import struct
from typing import Any

# This packet parser just extracts the useful "good parts".
#
# Combined fields have an underscore prefix (e.g. _verlen). Postprocess
# the output dictionary if you need to break these down further.

int_report_fixed_header = (
    "!B3xII4x",
    "_verlen",  # combined ver and len
    "switch_id",
    "seq_num",
)

eth_ip_udp_header = (
    "!12xH12xIIHHH2x",
    "eth_type",
    "ipv4_src",
    "ipv4_dst",
    "udp4_src",
    "udp4_dst",
    "udp4_len",
)

intl4_shim = (
    "!BxBx",
    "int_type",
    "len",
)

int_header = (
    "!2xBBH2x",
    "_hop_metadata_len",  # low 5 bits only (high 3 bits are reserved)
    "remaining_hop_cnt",
    "instruction_mask",
)

int_switch_id = ("!I", "switch_id")
int_port_ids = ("!HH", "ingress_port_id", "egress_port_id")
int_hop_latency = ("!I", "hop_latency")
int_q_occupancy = ("!I", "_q_occupancy")  # combined q_id and q_occupancy
int_ingress_tstamp = ("!Q", "ingress_tstamp")
int_egress_tstamp = ("!Q", "egress_tstamp")
int_level2_port_ids = ("!HH", "l2_ingress_port_id", "l2_egress_port_id")
int_egress_port_tx_util = ("!I", "egress_port_tx_util")

MIN_MSG_LEN = sum(
    struct.calcsize(hdr[0])
    for hdr in [int_report_fixed_header, eth_ip_udp_header, intl4_shim]
)
HeaderSpec = tuple[str, ...]
Header = dict[str, Any]


def _parse_hdr(msg: bytes, header: HeaderSpec, result: Header) -> bytes:
    "Parse an individual header into a result dictionary."
    fmt = header[0]
    result.update(zip(header[1:], struct.unpack_from(fmt, msg)))
    return msg[struct.calcsize(fmt) :]


def _parse_hdr_if(
    condition: Any, msg: bytes, header: HeaderSpec, result: Header
) -> bytes:
    "Parse an individual header if condition is true."
    if condition:
        return _parse_hdr(msg, header, result)
    return msg


def _parse_int_node(mask: int, msg: bytes, result: Header) -> bytes:
    "Parse an INT node."
    node: Header = {}
    msg = _parse_hdr_if(mask & 0x8000, msg, int_switch_id, node)
    msg = _parse_hdr_if(mask & 0x4000, msg, int_port_ids, node)
    msg = _parse_hdr_if(mask & 0x2000, msg, int_hop_latency, node)
    msg = _parse_hdr_if(mask & 0x1000, msg, int_q_occupancy, node)
    msg = _parse_hdr_if(mask & 0x0800, msg, int_ingress_tstamp, node)
    msg = _parse_hdr_if(mask & 0x0400, msg, int_egress_tstamp, node)
    msg = _parse_hdr_if(mask & 0x0200, msg, int_level2_port_ids, node)
    msg = _parse_hdr_if(mask & 0x0100, msg, int_egress_port_tx_util, node)
    result["nodes"].append(node)
    return msg


def parse_msg(msg: bytes) -> tuple[Header | None, bytes]:
    "Parse the INT message into a dictionary and the leftover bytes."
    start = msg
    if len(msg) < MIN_MSG_LEN:
        return None, start

    result: Header = {}

    msg = _parse_hdr(msg, int_report_fixed_header, result)
    if result["_verlen"] != 0x14:
        raise ValueError(f"unexpected _verlen: {result['_verlen']}")

    msg = _parse_hdr(msg, eth_ip_udp_header, result)
    msg = _parse_hdr(msg, intl4_shim, result)

    int_len = result["len"] * 4 - 4
    if len(msg) < int_len:
        return None, start
    msg, leftover = msg[:int_len], msg[int_len:]

    msg = _parse_hdr(msg, int_header, result)
    mask = result["instruction_mask"]
    result["nodes"] = []

    while msg:
        msg = _parse_int_node(mask, msg, result)

    return result, leftover


if __name__ == "__main__":
    val, left = parse_msg(
        bytes.fromhex(
            "140000400000000200000000000000000000000002020000000001010800458000a6ac064000401176be0a0001010a00020281de15b3009204760100210010000a01ff000000000000020000000409272cc10000000000000023c0e32ce800000023c106d1e800000000000000000000000300020003000004f20000000000000023bd141bb800000023bd276d0800000000000000000000000100010003000007610000000000000023c3e155a000000023c3fe28880000000000000000FF"
        )
    )
    print(val)
