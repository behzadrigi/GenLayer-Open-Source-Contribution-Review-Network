import json
import pytest
from genlayer_py import create_client, create_account
from genlayer_py.chains import localnet

CONTRACT_ADDRESS = "0x0714eAa835AC16911426f337a27DD7797d0904b5"


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
    assert 0 <= data["impact_score"] <= 100
    assert data["status"] == "SCORED"


def test_cannot_score_twice(client):
    with pytest.raises(Exception, match="Already scored"):
        _write(client, "score_impact", [0])


def test_list_scores(client):
    listing = _read(client, "list_scores")
    assert listing.startswith("0:")
