import grpc

from finsy import GRPCStatusCode, P4Client, P4ClientError, pbuf
from finsy.p4client import P4SubError
from finsy.proto import U128, p4r, rpc_status


async def test_client(p4rt_server_target):
    "Test P4Client."

    client = P4Client(p4rt_server_target)
    async with client:
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
        initial_metadata=[],
        trailing_metadata=meta,
        details="outer message",
    )

    err = P4ClientError(ex, "test_client_error")
    assert err.code == GRPCStatusCode.UNKNOWN
    assert not err.is_unimplemented
    assert err.message == "inner message"
    assert err.details == {
        0: P4SubError(
            canonical_code=GRPCStatusCode.NOT_FOUND,
            message="sub message",
            space="",
            code=0,
            subvalue=None,
        )
    }

    assert err.status.is_not_found_only
