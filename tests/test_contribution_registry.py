import json
import pytest
from genlayer_py import create_client, create_account
from genlayer_py.chains import localnet

CONTRACT_ADDRESS = "0x18D4d1E86eFBB0c6fE009c88fE9798975d13A9D3"


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


def test_invalid_repo_url_rejected(client):
    with pytest.raises(Exception, match="Invalid repo URL"):
        _write(client, "submit_contribution", [
            "not_a_url", "https://github.com/x/y/pull/1", "test",
        ])


def test_invalid_pr_url_rejected(client):
    with pytest.raises(Exception, match="Invalid PR URL"):
        _write(client, "submit_contribution", [
            "https://github.com/psf/requests", "not_a_url", "test",
        ])


def test_submit_valid_contribution(client):
    _write(client, "submit_contribution", [
        "https://github.com/autobrr/autobrr",
        "https://github.com/autobrr/autobrr/pull/2688",
        "Fixes a bug where saving a filter shows 0/0 for action counts until "
        "the page is reloaded. Invalidates filter-list queries after saving.",
    ])
    contribution_id = 0
    details = json.loads(_read(client, "get_contribution_details", [contribution_id]))
    assert details["status"] == "PENDING"


def test_agent_bound_to_sender(client):
    data = json.loads(_read(client, "get_contribution_data", [0]))
    assert data["agent"] != ""  # bound to gl.message.sender_address


def test_empty_description_rejected(client):
    with pytest.raises(Exception, match="Description cannot be empty"):
        _write(client, "submit_contribution", [
            "https://github.com/autobrr/autobrr",
            "https://github.com/autobrr/autobrr/pull/2688",
            "",
        ])


def test_list_contributions(client):
    listing = _read(client, "list_contributions")
    assert "0:PENDING" in listing
