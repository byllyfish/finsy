from unittest.mock import Mock

import pytest
from finsy.grpcutil import GRPCStatusCode
from finsy.p4arbitrator import Arbitrator
from finsy.p4client import P4Client
from finsy.proto import U128, p4r, rpc_status


def _mock_switch(receive_returns):
    "Return a Mock object representing a Switch with a mocked client."

    replies = [
        p4r.StreamMessageResponse(
            arbitration=p4r.MasterArbitrationUpdate(
                device_id=1,
                election_id=U128.encode(election_id),
                status=rpc_status.Status(code=code),
            )
        )
        for election_id, code in receive_returns
    ]

    p4client = Mock(P4Client)
    p4client.receive.side_effect = replies

    switch = Mock()
    switch.device_id = 1
    switch._p4client = p4client

    return switch


async def test_arbitrator_handshake_primary():
    "Test the Arbitrator class handshake method."

    arbitrator = Arbitrator(100)

    assert not arbitrator.is_primary
    assert arbitrator.initial_election_id == 100
    assert arbitrator.election_id == 100

    switch = _mock_switch([(100, GRPCStatusCode.OK)])
    await arbitrator.handshake(switch)

    assert arbitrator.is_primary
    assert arbitrator.primary_id == 100
    assert arbitrator.election_id == 100


async def test_arbitrator_handshake_invalid1():
    "Test the Arbitrator class handshake method with an invalid response."

    arbitrator = Arbitrator(100)

    assert not arbitrator.is_primary
    assert arbitrator.initial_election_id == 100
    assert arbitrator.election_id == 100

    # Client returns election_id 101 with OK response.
    switch = _mock_switch([(101, GRPCStatusCode.OK)])

    with pytest.raises(RuntimeError, match="primary invariant failed"):
        await arbitrator.handshake(switch)


async def test_arbitrator_handshake_invalid2():
    "Test the Arbitrator class handshake method with an invalid response."

    arbitrator = Arbitrator(100)

    assert not arbitrator.is_primary
    assert arbitrator.initial_election_id == 100
    assert arbitrator.election_id == 100

    # Client returns election_id 99 with ALREADY_EXISTS response.
    switch = _mock_switch([(99, GRPCStatusCode.ALREADY_EXISTS)])

    with pytest.raises(RuntimeError, match="backup invariant failed"):
        await arbitrator.handshake(switch)


async def test_arbitrator_handshake_missing_primary():
    "Test the Arbitrator class handshake method with a missing primary."

    arbitrator = Arbitrator(100)

    assert not arbitrator.is_primary
    assert arbitrator.initial_election_id == 100
    assert arbitrator.election_id == 100

    # We see that there is a missing primary (110), so we become the primary.
    switch = _mock_switch(
        [
            (110, GRPCStatusCode.NOT_FOUND),
            (110, GRPCStatusCode.OK),
        ]
    )

    await arbitrator.handshake(switch)

    assert arbitrator.is_primary
    assert arbitrator.election_id == 110
    assert arbitrator.primary_id == 110


def test_complete_request():
    "Test the arbitrator's `complete_request` method."

    arbitrator = Arbitrator(100)

    for msg_type in (p4r.SetForwardingPipelineConfigRequest, p4r.WriteRequest):
        msg = msg_type()
        arbitrator.complete_request(msg)
        assert U128.decode(msg.election_id) == arbitrator.election_id
