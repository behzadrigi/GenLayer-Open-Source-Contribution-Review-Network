import json
import pytest
from genlayer_py import create_client, create_account
from genlayer_py.chains import localnet

CONTRACT_ADDRESS = "0x0c9792f09f9bED0D5774988F82Fb99D5C6BE6B1c"

ALLOWED_CATEGORIES = ("BUGFIX", "FEATURE", "DOCS", "REFACTOR", "OTHER")


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


def test_classify(client):
    """Assumes contribution_id=0 from test_contribution_registry.py already exists."""
    _write(client, "classify", [0])
    data = json.loads(_read(client, "get_classification_data", [0]))
    assert data["category"] in ALLOWED_CATEGORIES
    assert data["status"] == "CLASSIFIED"


def test_cannot_classify_twice(client):
    with pytest.raises(Exception, match="Already classified"):
        _write(client, "classify", [0])


def test_list_classifications(client):
    listing = _read(client, "list_classifications")
    assert "0:" in listing
