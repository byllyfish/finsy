import asyncio
from pathlib import Path

import pytest

import finsy as fy
from finsy.test import demonet as dn

TEST_CERTS = Path(__file__).parents[2] / "tests/test_certs"


def demonet(model: str, cacert: Path, cert: Path, private_key: Path):
    return dn.DemoNet(
        [
            dn.Switch(
                "s1",
                model=model,
                grpc_cacert=cacert,
                grpc_cert=cert,
                grpc_private_key=private_key,
            )
        ]
    )


def tls_server(dir: str):
    return {
        "cacert": TEST_CERTS / dir / "ca.crt",
        "cert": TEST_CERTS / dir / "server.crt",
        "private_key": TEST_CERTS / dir / "server.key",
    }


def tls_client(dir: str):
    return {
        "cacert": TEST_CERTS / dir / "ca.crt",
        "cert": TEST_CERTS / dir / "client.crt",
        "private_key": TEST_CERTS / dir / "client.key",
    }


@pytest.mark.parametrize("model", ["bmv2", "stratum"])
async def test_mtls1(model):
    "Test switches using mtls1."
    creds = fy.GRPCCredentialsTLS(**tls_client("mtls1"))
    opts = fy.SwitchOptions(channel_credentials=creds)

    async with demonet(model, **tls_server("mtls1")) as net:
        await asyncio.sleep(0.25)

        async with fy.Switch("s1", "127.0.0.1:50001", opts) as sw:
            assert sw.is_up


# FIXME: this test fails for stratum???
@pytest.mark.parametrize("model", ["bmv2"])  # , "stratum"])
async def test_mtls3_expired_client(model):
    "Test switches using mtls3_expired_client."
    creds = fy.GRPCCredentialsTLS(**tls_client("mtls3_expired_client"))
    opts = fy.SwitchOptions(channel_credentials=creds)

    async with demonet(model, **tls_server("mtls3_expired_client")) as net:
        await asyncio.sleep(0.25)

        with pytest.raises(fy.P4ClientError, match="Socket closed"):
            async with fy.Switch("s1", "127.0.0.1:50001", opts) as sw:
                pass


@pytest.mark.parametrize("model", ["bmv2", "stratum"])
async def test_mtls4_expired_server(model):
    "Test switches using mtls4_expired_server."
    creds = fy.GRPCCredentialsTLS(**tls_client("mtls4_expired_server"))
    opts = fy.SwitchOptions(channel_credentials=creds)

    async with demonet(model, **tls_server("mtls4_expired_server")) as net:
        await asyncio.sleep(0.25)

        with pytest.raises(fy.P4ClientError, match="Ssl handshake failed"):
            async with fy.Switch("s1", "127.0.0.1:50001", opts) as sw:
                pass


@pytest.mark.parametrize("model", ["bmv2", "stratum"])
async def test_mtls_mismatched(model):
    "Test switches using mtls1 and mtls2 (mismatched)."
    creds = fy.GRPCCredentialsTLS(**tls_client("mtls1"))
    opts = fy.SwitchOptions(channel_credentials=creds)

    async with demonet(model, **tls_server("mtls2")) as net:
        await asyncio.sleep(0.25)

        with pytest.raises(fy.P4ClientError, match="Ssl handshake failed"):
            async with fy.Switch("s1", "127.0.0.1:50001", opts) as sw:
                pass
