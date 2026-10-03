import json
import pytest
from genlayer_py import create_client, create_account
from genlayer_py.chains import localnet

CONTRACT_ADDRESS = "0x9D2EfcdD7089ba974d65373Ba1084690fcAFe8a2"
IMPACT_BUCKETS = (10, 30, 50, 70, 90)


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


def test_score_impact(client):
    """Assumes contribution_id=0 from test_contribution_registry.py already exists."""
    _write(client, "score_impact", [0])
    data = json.loads(_read(client, "get_impact_data", [0]))
    # The score must be one of the fixed discrete buckets — never an
    # arbitrary in-between value. This is what closes the tolerance-band
    # gap a reviewer flagged: a continuous 0-100 score with a tolerance
    # window let the same contribution validly land on either side of the
    # 50-point approval threshold.
    assert data["impact_score"] in IMPACT_BUCKETS
    assert data["status"] == "SCORED"


def test_cannot_score_twice(client):
    with pytest.raises(Exception, match="Already scored"):
        _write(client, "score_impact", [0])


def test_score_nonexistent_contribution(client):
    with pytest.raises(Exception, match="Contribution not found in registry"):
        _write(client, "score_impact", [999])


def test_list_scores(client):
    listing = _read(client, "list_scores")
    assert listing.startswith("0:")
