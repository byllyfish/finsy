import asyncio
import dataclasses
from urllib.parse import urlparse

import grpc
import pytest

from finsy import GRPCStatusCode, P4Client, P4ClientError, P4Error, pbutil
from finsy.proto import U128, p4r, rpc_status
from finsy.test.p4runtime_server import P4RuntimeServer

from .test_certs import (
    CLIENT1_CREDS,
    CLIENT1_MISCONFIG_CREDS,
    CLIENT1_MISSING_CREDS,
    CLIENT2_CREDS,
    CLIENT3_CREDS_XCLIENT,
    CLIENT4_CREDS_XSERVER,
    CLIENT5_CREDS,
    SERVER1_CREDS,
    SERVER3_CREDS_XCLIENT,
    SERVER4_CREDS_XSERVER,
    SERVER5_CREDS_NO_IP,
)


async def test_insecure_client_vs_insecure_server(p4rt_server_target):
    "Test insecure P4Client."
    client = P4Client(p4rt_server_target, wait_for_ready=False)
    async with client:
        await _check_arbitration_request(client)


async def test_tls_client_vs_tls_server(p4rt_secure_server):
    "Test TLS P4Client."
    client = P4Client(*p4rt_secure_server, wait_for_ready=False)
    async with client:
        await _check_arbitration_request(client)


async def test_wrong_tls_client_vs_tls_server(p4rt_secure_server):
    "Test TLS P4Client using the wrong certificate for a server."
    client = P4Client(p4rt_secure_server[0], CLIENT2_CREDS, wait_for_ready=False)
    async with client:
        with pytest.raises(P4ClientError, match="Ssl handshake failed:"):
            await _check_arbitration_request(client)


async def test_wrong_tls_client_vs_tls_server_wait_for_ready(p4rt_secure_server):
    "Test TLS P4Client using wrong certificate for a server (wait_for_ready)."
    client = P4Client(p4rt_secure_server[0], CLIENT2_CREDS, wait_for_ready=True)
    async with client:
        # FIXME: When using wait_for_ready, we need to check for failure. GRPC
        # does not surface TLS errors or alerts. Problems will be logged to
        # stderr, but that might be obscured. The Timeout here is needed
        # because GRPC will just keep going...
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(_check_arbitration_request(client), 2.0)


# On Windows, the "Socket closed" message is "End of TCP stream".
_UNAVAILABLE1 = "UNAVAILABLE:.*: (?:Socket closed|End of TCP stream)"
# On Windows, the "Connection reset by peer" message is "Connection aborted".
_UNAVAILABLE2 = "UNAVAILABLE:.*: (?:Socket closed|End of TCP stream|recvmsg:Connection reset by peer|Connection aborted)"


async def test_insecure_client_vs_tls_server(p4rt_secure_server):
    "Test insecure P4Client against a TLS server."
    client = P4Client(p4rt_secure_server[0], wait_for_ready=False)
    async with client:
        with pytest.raises(P4ClientError, match=_UNAVAILABLE1):
            await _check_arbitration_request(client)


async def test_tls_client_vs_insecure_server(p4rt_server_target):
    "Test TLS P4Client against an insecure server."
    client = P4Client(p4rt_server_target, CLIENT1_CREDS, wait_for_ready=False)
    async with client:
        with pytest.raises(
            P4ClientError, match="Ssl handshake failed:.*:WRONG_VERSION_NUMBER"
        ):
            await _check_arbitration_request(client)


async def test_expired_tls_client_vs_tls_server(unused_tcp_target):
    "Test TLS P4Client with an expired client certificate."
    server = P4RuntimeServer(unused_tcp_target, credentials=SERVER3_CREDS_XCLIENT)
    async with server.run():
        client = P4Client(
            unused_tcp_target, CLIENT3_CREDS_XCLIENT, wait_for_ready=False
        )
        async with client:
            with pytest.raises(P4ClientError, match=_UNAVAILABLE1):
                await _check_arbitration_request(client)


async def test_tls_client_vs_expired_tls_server(unused_tcp_target):
    "Test TLS P4Client against a server with an expired certificate."
    server = P4RuntimeServer(unused_tcp_target, credentials=SERVER4_CREDS_XSERVER)
    async with server.run():
        client = P4Client(
            unused_tcp_target, CLIENT4_CREDS_XSERVER, wait_for_ready=False
        )
        async with client:
            with pytest.raises(
                P4ClientError, match="Ssl handshake failed:.*:CERTIFICATE_VERIFY_FAILED"
            ):
                await _check_arbitration_request(client)


async def test_tls_client_vs_tls_server_missing_client_cert(p4rt_secure_server):
    "Test TLS P4Client with a missing client certificate."
    client = P4Client(
        p4rt_secure_server[0], CLIENT1_MISSING_CREDS, wait_for_ready=False
    )
    async with client:
        with pytest.raises(P4ClientError, match=_UNAVAILABLE2):
            await _check_arbitration_request(client)


async def test_tls_client_using_misconfigured_key(p4rt_secure_server):
    "Test TLS client using misconfigured certificate/private key pair."
    client = P4Client(
        p4rt_secure_server[0], CLIENT1_MISCONFIG_CREDS, wait_for_ready=False
    )
    async with client:
        with pytest.raises(
            P4ClientError,
            match="code=GRPCStatusCode.UNAVAILABLE message='empty address list: '",
        ):
            await _check_arbitration_request(client)


async def test_tls_client_using_wrong_name(unused_tcp_port):
    "Test TLS client using ::1 loopback address (certs only configured for IPv4)."
    target = f"127.0.0.1:{unused_tcp_port}"
    server = P4RuntimeServer(target, credentials=SERVER5_CREDS_NO_IP)
    async with server.run():
        client = P4Client(target, CLIENT5_CREDS, wait_for_ready=False)
        async with client:
            with pytest.raises(
                P4ClientError,
                match="Peer name 127.0.0.1 is not in peer certificate",
            ):
                await _check_arbitration_request(client)


async def test_tls_client_target_name_override(unused_tcp_port):
    "Test TLS client using ::1 loopback address with target name override."
    target = f"127.0.0.1:{unused_tcp_port}"
    server = P4RuntimeServer(target, credentials=SERVER5_CREDS_NO_IP)
    async with server.run():
        creds = dataclasses.replace(CLIENT5_CREDS)
        creds.target_name_override = "localhost"
        client = P4Client(target, creds, wait_for_ready=False)
        async with client:
            await _check_arbitration_request(client)


async def test_tls_client_using_server_cert(p4rt_secure_server):
    "Test TLS client using a server certificate."
    client = P4Client(p4rt_secure_server[0], SERVER1_CREDS, wait_for_ready=False)
    async with client:
        with pytest.raises(P4ClientError, match=_UNAVAILABLE1):
            await _check_arbitration_request(client)


async def _check_arbitration_request(client: P4Client):
    "Send an arbitration request and check the arbitration reply."
    await client.send(
        p4r.StreamMessageRequest(
            arbitration=p4r.MasterArbitrationUpdate(
                device_id=1,
                election_id=U128.encode(1),
            )
        )
    )
    reply = await client.receive()
    assert pbutil.to_dict(reply) == {
        "arbitration": {"device_id": "1", "election_id": {"low": "1"}}
    }


def test_client_error():
    "Test P4ClientError exception class."
    status = rpc_status.Status(
        code=GRPCStatusCode.UNKNOWN,
        message="inner message",
        details=[
            pbutil.to_any(
                p4r.Error(
                    canonical_code=GRPCStatusCode.NOT_FOUND,
                    message="sub message",
                )
            ),
            pbutil.to_any(
                p4r.Error(
                    canonical_code=GRPCStatusCode.OK,
                    message="okay",
                ),
            ),
        ],
    )
    meta = grpc.aio.Metadata(
        ("a", b"b"),
        ("grpc-status-details-bin", status.SerializeToString()),
    )

    ex = grpc.aio.AioRpcError(
        code=grpc.StatusCode.INTERNAL,
        initial_metadata=grpc.aio.Metadata(),
        trailing_metadata=meta,
        details="outer message",
    )

    err = P4ClientError(ex, "test_client_error")
    assert err.code == GRPCStatusCode.UNKNOWN
    assert err.message == "inner message"
    assert err.details == {
        0: P4Error(
            canonical_code=GRPCStatusCode.NOT_FOUND,
            message="sub message",
            space="",
            code=0,
            subvalue=None,
        )
    }

    assert err.is_not_found_only
    assert not err.is_election_id_used
    assert not err.is_pipeline_missing


async def test_tls_client_call_creds(p4rt_secure_server):
    "Test TLS P4Client with a call credential object."
    method_names = []

    def _creds(context, callback):
        # Be careful. This function is called in a *different* Python thread.
        path = urlparse(context.service_url).path
        method_names.append((path, context.method_name))
        callback([("x-credentials", "abc")], None)

    creds = dataclasses.replace(CLIENT1_CREDS, call_credentials=_creds)
    client = P4Client(p4rt_secure_server[0], creds, wait_for_ready=False)
    async with client:
        await _check_arbitration_request(client)
        await client.request(p4r.CapabilitiesRequest())

    assert method_names == [
        ("/p4.v1.P4Runtime", "StreamChannel"),
        ("/p4.v1.P4Runtime", "Capabilities"),
    ]
