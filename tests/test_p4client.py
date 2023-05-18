import grpc
import pytest

from finsy import GRPCStatusCode, P4Client, P4ClientError, P4Error, pbuf
from finsy.proto import U128, p4r, rpc_status
from finsy.test.p4runtime_server import P4RuntimeServer

from .test_certs import (
    CLIENT1_CREDS,
    CLIENT2_CREDS,
    CLIENT3_CREDS_XCLIENT,
    CLIENT4_CREDS_XSERVER,
    SERVER3_CREDS_XCLIENT,
    SERVER4_CREDS_XSERVER,
)


async def test_insecure_client_vs_insecure_server(p4rt_server_target):
    "Test insecure P4Client."
    client = P4Client(p4rt_server_target, wait_for_ready=False)
    async with client:
        await _check_arbitration_request(client)


async def test_tls_client_vs_tls_server(p4rt_secure_server):
    "Test P4Client using TLS."
    client = P4Client(*p4rt_secure_server, wait_for_ready=False)
    async with client:
        await _check_arbitration_request(client)


async def test_wrong_tls_client_vs_tls_server(p4rt_secure_server):
    "Test P4Client using TLS."
    client = P4Client(p4rt_secure_server[0], CLIENT2_CREDS, wait_for_ready=False)
    async with client:
        with pytest.raises(P4ClientError, match="Ssl handshake failed:"):
            await _check_arbitration_request(client)


async def test_insecure_client_vs_tls_server(p4rt_secure_server):
    "Test P4Client."
    client = P4Client(p4rt_secure_server[0], wait_for_ready=False)
    async with client:
        with pytest.raises(P4ClientError, match="UNAVAILABLE:.*: Socket closed"):
            await _check_arbitration_request(client)


async def test_tls_client_vs_insecure_server(p4rt_server_target):
    "Test P4Client."
    client = P4Client(p4rt_server_target, CLIENT1_CREDS, wait_for_ready=False)
    async with client:
        with pytest.raises(
            P4ClientError, match="Ssl handshake failed:.*:WRONG_VERSION_NUMBER"
        ):
            await _check_arbitration_request(client)


async def test_expired_tls_client_vs_tls_server(unused_tcp_target):
    "Test P4Client using TLS."
    server = P4RuntimeServer(unused_tcp_target, credentials=SERVER3_CREDS_XCLIENT)
    async with server.run():
        client = P4Client(
            unused_tcp_target, CLIENT3_CREDS_XCLIENT, wait_for_ready=False
        )
        async with client:
            await _check_arbitration_request(client)


async def test_tls_client_vs_expired_tls_server(unused_tcp_target):
    "Test P4Client using TLS."
    server = P4RuntimeServer(unused_tcp_target, credentials=SERVER4_CREDS_XSERVER)
    async with server.run():
        client = P4Client(
            unused_tcp_target, CLIENT4_CREDS_XSERVER, wait_for_ready=False
        )
        async with client:
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
    assert pbuf.to_dict(reply) == {
        "arbitration": {"device_id": "1", "election_id": {"low": "1"}}
    }


def test_client_error():
    "Test P4ClientError exception class."
    status = rpc_status.Status(
        code=GRPCStatusCode.UNKNOWN,
        message="inner message",
        details=[
            pbuf.to_any(
                p4r.Error(
                    canonical_code=GRPCStatusCode.NOT_FOUND,
                    message="sub message",
                )
            ),
            pbuf.to_any(
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
