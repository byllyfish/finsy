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

    async with demonet(model, **tls_server("mtls1")):
        await asyncio.sleep(0.25)

        async with fy.Switch("s1", "127.0.0.1:50001", opts) as sw:
            assert sw.is_up


# NOTE: This test fails for stratum. stratum doesn't check client certificates.
@pytest.mark.parametrize("model", ["bmv2"])  # , "stratum"])
async def test_mtls3_expired_client(model):
    "Test switches using mtls3_expired_client."
    creds = fy.GRPCCredentialsTLS(**tls_client("mtls3_expired_client"))
    opts = fy.SwitchOptions(channel_credentials=creds)

    async with demonet(model, **tls_server("mtls3_expired_client")):
        await asyncio.sleep(0.25)

        with pytest.raises(fy.P4ClientError, match="Socket closed"):
            async with fy.Switch("s1", "127.0.0.1:50001", opts):
                pass


@pytest.mark.parametrize("model", ["bmv2", "stratum"])
async def test_mtls4_expired_server(model):
    "Test switches using mtls4_expired_server."
    creds = fy.GRPCCredentialsTLS(**tls_client("mtls4_expired_server"))
    opts = fy.SwitchOptions(channel_credentials=creds)

    async with demonet(model, **tls_server("mtls4_expired_server")):
        await asyncio.sleep(0.25)

        with pytest.raises(fy.P4ClientError, match="Ssl handshake failed"):
            async with fy.Switch("s1", "127.0.0.1:50001", opts):
                pass


@pytest.mark.parametrize("model", ["bmv2", "stratum"])
async def test_mtls_mismatched(model):
    "Test switches using mtls1 and mtls2 (mismatched)."
    creds = fy.GRPCCredentialsTLS(**tls_client("mtls1"))
    opts = fy.SwitchOptions(channel_credentials=creds)

    async with demonet(model, **tls_server("mtls2")):
        await asyncio.sleep(0.25)

        with pytest.raises(fy.P4ClientError, match="Ssl handshake failed"):
            async with fy.Switch("s1", "127.0.0.1:50001", opts):
                pass


# NOTE: This test fails for stratum. stratum doesn't check client certificates.
@pytest.mark.parametrize("model", ["bmv2"])  # , "stratum"])
async def test_tls_no_client_cert(model):
    "Test switches using TLS without a client cert."
    settings = {
        "cacert": TEST_CERTS / "mtls1" / "ca.crt",
        "cert": None,
        "private_key": None,
    }
    creds = fy.GRPCCredentialsTLS(**settings)
    opts = fy.SwitchOptions(channel_credentials=creds)

    async with demonet(model, **tls_server("mtls1")):
        await asyncio.sleep(0.25)

        with pytest.raises(fy.P4ClientError, match="Socket closed"):
            async with fy.Switch("s1", "127.0.0.1:50001", opts):
                pass
