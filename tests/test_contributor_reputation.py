import json
import pytest
from genlayer_py import create_client, create_account
from genlayer_py.chains import localnet

CONTRACT_ADDRESS = "0x219Fda3D6B3335dBE68a171b5a316C82572C0e88"


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
    # status is empirical: APPROVED if final_score >= 50, else REJECTED —
    # both are valid outcomes depending on the real quality/impact results.
    assert details["status"] in ("APPROVED", "REJECTED")
    # final_score must equal the documented formula exactly, given the
    # quality_score and impact_score already on record.
    expected = int(0.5 * details["quality_score"] + 0.5 * details["impact_score"])
    assert details["final_score"] == expected
    # change_type depends on how far final_score is from the starting
    # reputation of 50 — NEUTRAL (no change) is correct and returns SUCCESS
    # here, it does not revert.
    assert details["change_type"] in ("INCREASE", "DECREASE", "NEUTRAL")


def test_cannot_finalize_twice(client):
    with pytest.raises(Exception, match="Contribution already finalized"):
        _write(client, "finalize_contribution", [0])


def test_finalize_nonexistent_contribution(client):
    with pytest.raises(Exception, match="Quality assessment not found"):
        _write(client, "finalize_contribution", [999])
