#!/usr/bin/env python3

from finsy.test import demonet as dn

DEMONET = [
    dn.Image("docker.io/opennetworking/p4mn"),
    dn.Switch("s1"),
    dn.Switch("s2"),
    dn.Switch("s3"),
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
    dn.Switch("br1", model="linux"),
    dn.Host("intc", "br1", mac="00:00:00:00:09:09", ipv4="10.0.9.9/8"),
    dn.Link("s1", "br1", style="dotted"),
    dn.Link("s2", "br1", style="dotted"),
    dn.Link("s3", "br1", style="dotted"),
]

if __name__ == "__main__":
    dn.main(DEMONET)
