from finsy import P4Client, pbuf
from finsy.proto import U128, p4r


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
