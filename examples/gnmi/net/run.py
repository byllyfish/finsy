#!/usr/bin/env python3

from finsy.test import demonet as dn

DEMONET = [
    dn.Image("docker.io/opennetworking/mn-stratum"),
    dn.Switch("s1"),
    dn.Host("h1", "s1"),
]

if __name__ == "__main__":
    dn.main(DEMONET)
