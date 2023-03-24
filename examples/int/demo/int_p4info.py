import finsy as fy

# TODO: generate these stubs automatically from p4info.txt file.


def tb_activate_source__activate_source(*, ingress_port: int):
    return fy.P4TableEntry(
        "tb_activate_source",
        match=fy.P4TableMatch(ingress_port=ingress_port),
        action=fy.P4TableAction("activate_source"),
    )


def tb_int_source__configure_source(
    *,
    priority: int,
    srcAddr: str,
    dstAddr: str,
    l4_src: int | str,
    l4_dst: int | str,
    max_hop: int,
    hop_metadata_len: int,
    ins_cnt: int,
    ins_mask: int,
):
    return fy.P4TableEntry(
        "tb_int_source",
        priority=priority,
        match=fy.P4TableMatch(
            srcAddr=srcAddr,
            dstAddr=dstAddr,
            l4_src=l4_src,
            l4_dst=l4_dst,
        ),
        action=fy.P4TableAction(
            "configure_source",
            max_hop=max_hop,
            hop_metadata_len=hop_metadata_len,
            ins_cnt=ins_cnt,
            ins_mask=ins_mask,
        ),
    )


def tb_int_sink__configure_sink(
    *,
    egress_spec: int,
    sink_reporting_port: int,
):
    return fy.P4TableEntry(
        "tb_int_sink",
        match=fy.P4TableMatch(egress_spec=egress_spec),
        action=fy.P4TableAction(
            "configure_sink",
            sink_reporting_port=sink_reporting_port,
        ),
    )


def tb_int_reporting__send_report(
    *,
    dp_mac: str,
    dp_ip: str,
    collector_mac: str,
    collector_ip: str,
    collector_port: int,
):
    return fy.P4TableEntry(
        "tb_int_reporting",
        action=fy.P4TableAction(
            "send_report",
            dp_mac=dp_mac,
            dp_ip=dp_ip,
            collector_mac=collector_mac,
            collector_ip=collector_ip,
            collector_port=collector_port,
        ),
    )


def tb_int_transit__configure_transit(
    *,
    switch_id: int,
    l3_mtu: int,
):
    return fy.P4TableEntry(
        "tb_int_transit",
        action=fy.P4TableAction(
            "configure_transit",
            switch_id=switch_id,
            l3_mtu=l3_mtu,
        ),
    )


def tb_forward__send_to_port(
    *,
    priority: int,
    dstAddr: str,
    port: int,
):
    return fy.P4TableEntry(
        "tb_forward",
        priority=priority,
        match=fy.P4TableMatch(dstAddr=dstAddr),
        action=fy.P4TableAction("send_to_port", port=port),
    )


def tb_forward__send_to_cpu(
    *,
    priority: int,
    dstAddr: str,
    port: int,
):
    return fy.P4TableEntry(
        "tb_forward",
        priority=priority,
        match=fy.P4TableMatch(dstAddr=dstAddr),
        action=fy.P4TableAction("send_to_cpu", port=port),
    )
