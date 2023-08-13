#!/usr/bin/env python3

from finsy.test import demonet as dn

DEMONET = [
    dn.Switch("s1"),
    dn.Switch("s2"),
    dn.Switch("s3"),
    dn.Link("s1", "s2"),
    dn.Link("s1", "s3"),
    dn.Link("s2", "s3"),
    dn.Host(
        "h1",
        "s1",
        mac="08:00:00:00:01:11",
        ipv4="10.0.1.1/24",
        ipv4_gw="10.0.1.10",
        static_arp={"10.0.1.10": "08:00:00:00:01:00"},
    ),
    dn.Host(
        "h2",
        "s2",
        mac="08:00:00:00:02:22",
        ipv4="10.0.2.2/24",
        ipv4_gw="10.0.2.20",
        static_arp={"10.0.2.20": "08:00:00:00:02:00"},
    ),
    dn.Host(
        "h3",
        "s3",
        mac="08:00:00:00:03:33",
        ipv4="10.0.3.3/24",
        ipv4_gw="10.0.3.30",
        static_arp={"10.0.3.30": "08:00:00:00:03:00"},
    ),
]

if __name__ == "__main__":
    dn.main(DEMONET)
