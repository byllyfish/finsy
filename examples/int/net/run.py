#!/usr/bin/env python3

from finsy.test import demonet as dn

DEMONET = [
    dn.Switch("s1", model="stratum"),
    dn.Switch("s2", model="stratum"),
    dn.Switch("s3", model="stratum"),
    dn.Host(
        "h1",
        "s1",
        mac="00:00:00:00:01:01",
        ipv4="10.0.1.1/8",
        static_arp={"10.0.2.2": "00:00:00:00:02:02"},
    ),
    dn.Host(
        "h2",
        "s2",
        mac="00:00:00:00:02:02",
        ipv4="10.0.2.2/8",
        static_arp={"10.0.1.1": "00:00:00:00:01:01"},
    ),
    dn.Host("h3", "s3", mac="00:00:00:00:03:03", ipv4="10.0.3.3/8"),
    dn.Link("s1", "s2"),
    dn.Link("s1", "s3"),
    dn.Link("s2", "s3"),
    # INT collection network.
    dn.Bridge(
        "int1",
        mac="00:00:00:00:09:09",
        ipv4="10.0.9.9/8",
        commands=[
            "socat udp-recvfrom:6000,fork tcp:$DEMONET_IP:6000 &",
        ],
    ),
    dn.Link("s1", "int1", style="dotted"),
    dn.Link("s2", "int1", style="dotted"),
    dn.Link("s3", "int1", style="dotted"),
]

if __name__ == "__main__":
    dn.main(DEMONET)
