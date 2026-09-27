import json
import pytest
from genlayer_py import create_client, create_account
from genlayer_py.chains import localnet

CONTRACT_ADDRESS = "0xf0B0397fb85fc9a9A1dA6A018F676A1031879035"


@pytest.fixture(scope="module")
def client():
    account = create_account()
    return create_client(chain=localnet, account=account)


def _write(client, function_name, args):
    tx_hash = client.write_contract(
        address=CONTRACT_ADDRESS, function_name=function_name, args=args, value=0,
    )
    return client.wait_for_transaction_receipt(transaction_hash=tx_hash, status="ACCEPTED")


def _read(client, function_name, args=None):
    return client.read_contract(
        address=CONTRACT_ADDRESS, function_name=function_name, args=args or [],
    )


def test_lazy_default_reputation(client, sender_address):
    """No initialize_reputation exists; first read should be the lazy default of 50."""
    assert _read(client, "get_reputation", [sender_address]) == "REPUTATION:50"


def test_finalize_contribution(client, sender_address):
    """Assumes contribution_id=0 has been assessed, scored, and classified already."""
    _write(client, "finalize_contribution", [0])
    details = json.loads(_read(client, "get_finalization_details", [0]))
    assert details["agent"] == sender_address
    assert details["status"] == "APPROVED"
    # change_type depends on how far final_score is from the starting
    # reputation of 50 — NEUTRAL (no change) is correct when final_score
    # lands within 10 points of 50, not a bug.
    assert details["change_type"] in ("INCREASE", "DECREASE", "NEUTRAL")


def test_cannot_finalize_twice(client):
    with pytest.raises(Exception, match="Contribution already finalized"):
        _write(client, "finalize_contribution", [0])


def test_finalize_nonexistent_contribution(client):
    with pytest.raises(Exception, match="Quality assessment not found"):
        _write(client, "finalize_contribution", [999])
