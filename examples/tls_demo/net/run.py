#!/usr/bin/env python3

from pathlib import Path

from finsy.test import demonet as dn

CERT_DIR = Path(__file__).parents[3] / "tests/test_certs/mtls1"

CACERT = CERT_DIR / "ca.crt"
CERT = CERT_DIR / "server.crt"
KEY = CERT_DIR / "server.key"

DEMONET = [
    dn.Switch("s1", grpc_cacert=CACERT, grpc_cert=CERT, grpc_private_key=KEY),
    dn.Switch(
        "s2", model="stratum", grpc_cacert=CACERT, grpc_cert=CERT, grpc_private_key=KEY
    ),
    dn.Host("h1", "s1"),
    dn.Host("h2", "s2"),
    dn.Link("s1", "s2"),
]

if __name__ == "__main__":
    dn.main(DEMONET)
