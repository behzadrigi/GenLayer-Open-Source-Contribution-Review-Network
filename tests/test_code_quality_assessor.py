import json
import pytest
from genlayer_py import create_client, create_account
from genlayer_py.chains import localnet

CONTRACT_ADDRESS = "0x540401Ed6b31dE2Bdeec897De8ab0f36b4c9ea90"


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


def test_assess_quality(client):
    """Assumes contribution_id=0 from test_contribution_registry.py already exists."""
    _write(client, "assess_quality", [0])
    data = json.loads(_read(client, "get_quality_data", [0]))
    assert isinstance(data["tests_added"], bool)
    assert isinstance(data["documented"], bool)
    assert isinstance(data["follows_style"], bool)
    assert data["status"] == "ASSESSED"


def test_cannot_assess_twice(client):
    with pytest.raises(Exception, match="Already assessed"):
        _write(client, "assess_quality", [0])


def test_assess_nonexistent_contribution(client):
    with pytest.raises(Exception, match="Contribution not found in registry"):
        _write(client, "assess_quality", [999])


def test_list_assessments(client):
    listing = _read(client, "list_assessments")
    assert "0:ASSESSED" in listing
