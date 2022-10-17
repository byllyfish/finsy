from unittest.mock import Mock

import pytest
from finsy.grpcutil import GRPCStatusCode
from finsy.p4arbitrator import Arbitrator
from finsy.p4client import P4Client
from finsy.proto import U128, p4r, rpc_status

_DEVICE_ID = 1


def _mock_switch(receive_returns):
    "Return a Mock object representing a Switch with a mocked client."

    replies = [
        p4r.StreamMessageResponse(
            arbitration=p4r.MasterArbitrationUpdate(
                device_id=_DEVICE_ID,
                election_id=U128.encode(election_id),
                status=rpc_status.Status(code=code),
            )
        )
        for election_id, code in receive_returns
    ]

    p4client = Mock(P4Client)
    p4client.receive.side_effect = replies

    switch = Mock()
    switch.device_id = _DEVICE_ID
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
    switch._p4client.send.assert_called_once()


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
    switch._p4client.send.assert_called()  # called twice


def test_complete_request():
    "Test the arbitrator's `complete_request` method."

    arbitrator = Arbitrator(100)

    for msg_type in (p4r.SetForwardingPipelineConfigRequest, p4r.WriteRequest):
        msg = msg_type()
        arbitrator.complete_request(msg)
        assert U128.decode(msg.election_id) == arbitrator.election_id


async def test_update_become_backup():
    """Test the arbitrator's `update` method with an ALREADY_EXISTS message
    when we are primary controller."""

    switch = _mock_switch([(100, GRPCStatusCode.OK)])

    # Perform initial handshake and become primary.
    arbitrator = Arbitrator(100)
    await arbitrator.handshake(switch)

    assert arbitrator.is_primary
    assert arbitrator.election_id == 100
    assert arbitrator.primary_id == 100

    switch._p4client.send.assert_called_once()
    switch._p4client.reset_mock()

    # Now call switch with subsequent MasterArbitrationUpdate message that
    # indicates another controller has taken over primary.
    msg = p4r.MasterArbitrationUpdate(
        device_id=_DEVICE_ID,
        election_id=U128.encode(101),
        status=rpc_status.Status(code=GRPCStatusCode.ALREADY_EXISTS),
    )

    await arbitrator.update(switch, msg)

    # We are no longer primary.
    assert not arbitrator.is_primary
    assert arbitrator.election_id == 100
    assert arbitrator.primary_id == 101

    switch._p4client.send.assert_not_called()
    switch._become_backup.assert_called_once()
    switch._become_primary.assert_not_called()


async def test_update_become_primary():
    """Test the arbitrator's `update` method with a NOT_FOUND message
    when we are backup controller."""

    switch = _mock_switch([(101, GRPCStatusCode.ALREADY_EXISTS)])

    # Perform initial handshake and become backup.
    arbitrator = Arbitrator(100)
    await arbitrator.handshake(switch)

    assert not arbitrator.is_primary
    assert arbitrator.election_id == 100
    assert arbitrator.primary_id == 101

    switch._p4client.send.assert_called_once()
    switch._p4client.reset_mock()

    # Now call switch with subsequent MasterArbitrationUpdate message that
    # indicates another controller relinquished primary.
    msg = p4r.MasterArbitrationUpdate(
        device_id=_DEVICE_ID,
        election_id=U128.encode(102),
        status=rpc_status.Status(code=GRPCStatusCode.NOT_FOUND),
    )
    await arbitrator.update(switch, msg)

    # We are no longer primary, but we're in the middle of renegotiation.
    assert not arbitrator.is_primary
    assert arbitrator.election_id == 102
    assert arbitrator.primary_id == 102
    # assert arbitrator.renegotiating

    switch._p4client.send.assert_called()
    switch._p4client.reset_mock()
    switch._become_backup.assert_not_called()
    switch._become_primary.assert_not_called()

    # We receive an update to our renegotiation offer.
    msg = p4r.MasterArbitrationUpdate(
        device_id=_DEVICE_ID,
        election_id=U128.encode(102),
        status=rpc_status.Status(code=GRPCStatusCode.OK),
    )
    await arbitrator.update(switch, msg)

    # Now we are the primary.
    assert arbitrator.is_primary
    assert arbitrator.election_id == 102
    assert arbitrator.primary_id == 102

    switch._become_backup.assert_not_called()
    switch._become_primary.assert_called()
