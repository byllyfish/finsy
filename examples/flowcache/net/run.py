#!/usr/bin/env python3

from finsy.test import demonet as dn

STATIC_ARP = {
    "10.0.0.1": "00:00:00:00:00:01",
    "10.0.0.2": "00:00:00:00:00:02",
}

DEMONET = [
    dn.Switch("s1", cpu_port=510, log_level="debug"),
    dn.Host("h1", "s1", static_arp=STATIC_ARP),
    dn.Host("h2", "s1", static_arp=STATIC_ARP),
]

if __name__ == "__main__":
    dn.main(DEMONET)
