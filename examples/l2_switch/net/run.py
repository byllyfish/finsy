#!/usr/bin/env python3

from finsy.test import demonet as dn


def linear(host_count: int):
    "Return a linear topology where each host is connected to its own switch."
    switches = [dn.Switch(f"s{idx}") for idx in range(1, host_count + 1)]
    hosts = [dn.Host(f"h{idx}", f"s{idx}") for idx in range(1, host_count + 1)]
    links = [dn.Link(f"s{idx}", f"s{idx+1}") for idx in range(1, host_count)]
    return switches + hosts + links


DEMONET = [
    dn.Image("docker.io/opennetworking/p4mn"),
    *linear(3),
]

if __name__ == "__main__":
    dn.main(DEMONET)
