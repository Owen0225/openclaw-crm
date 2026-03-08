import pytest
import os
from openclaw_crm.network import (
    add_signal, promote_signal, dismiss_signal,
    get_network_tree, get_network_value, check_competitor_guard,
    SIGNALS_RANGE
)
from openclaw_crm.pipeline import PIPELINE_RANGE, create_deal

@pytest.fixture(autouse=True)
def setup_env():
    os.environ["CRM_SPREADSHEET_ID"] = "test_id"
    yield
    if "CRM_SPREADSHEET_ID" in os.environ:
        del os.environ["CRM_SPREADSHEET_ID"]

def test_add_signal(mock_sheets_backend):
    res = add_signal({
        "source_client": "Alice",
        "channel": "slack",
        "signal_text": "Bob needs help",
        "mentioned_company": "BobCorp"
    })
    assert res["ok"] is True
    assert res["status"] == "new"
    
    rows = mock_sheets_backend.data[SIGNALS_RANGE]
    assert len(rows) == 2
    assert rows[1][1] == "Alice"
    assert rows[1][4] == "BobCorp"
    assert rows[1][5] == "new"

def test_promote_signal(mock_sheets_backend):
    add_signal({"source_client": "Alice", "mentioned_company": "BobCorp"})
    
    res = promote_signal(2)  # row 2 is the first signal
    assert res["ok"] is True
    assert res["deal"]["client"] == "BobCorp"
    
    # Check signal status
    rows = mock_sheets_backend.data[SIGNALS_RANGE]
    assert rows[1][5] == "promoted"
    
    # Check deal creation
    p_rows = mock_sheets_backend.data[PIPELINE_RANGE]
    assert len(p_rows) == 2
    assert p_rows[1][0] == "BobCorp"
    assert p_rows[1][2] == "network"
    assert p_rows[1][17] == "Alice"  # Referred By
    assert p_rows[1][18] == "Alice"  # Network Parent

def test_promote_signal_already_promoted(mock_sheets_backend):
    add_signal({"source_client": "Alice", "mentioned_company": "BobCorp"})
    promote_signal(2)
    
    res = promote_signal(2)
    assert res["ok"] is False
    assert "already promoted" in res["error"]

def test_dismiss_signal(mock_sheets_backend):
    add_signal({"source_client": "Alice", "mentioned_company": "BobCorp"})
    
    res = dismiss_signal(2)
    assert res["ok"] is True
    
    rows = mock_sheets_backend.data[SIGNALS_RANGE]
    assert rows[1][5] == "dismissed"

def test_get_network_tree_and_value(mock_sheets_backend):
    create_deal({"client": "Alice", "budget": "1000", "stage": "won"})
    create_deal({"client": "Bob", "budget": "2000", "stage": "lead", "referred_by": "Alice", "network_parent": "Alice"})
    create_deal({"client": "Charlie", "budget": "3000", "stage": "proposal", "network_parent": "Bob"})
    
    tree = get_network_tree()
    assert "Alice" in tree
    assert len(tree["Alice"]) == 1
    assert tree["Alice"][0]["client"] == "Bob"
    
    assert "Bob" in tree
    assert len(tree["Bob"]) == 1
    assert tree["Bob"][0]["client"] == "Charlie"
    
    val_alice = get_network_value("Alice")
    assert val_alice["direct_value"] == 1000
    assert val_alice["network_value"] == 2000  # only direct children currently counted in get_network_value
    assert val_alice["total"] == 3000

def test_check_competitor_guard(mock_sheets_backend):
    create_deal({"client": "ExistingCorp", "stage": "negotiation"})
    
    assert check_competitor_guard("NewCorp", "SourceCorp") is True
    assert check_competitor_guard("ExistingCorp", "SourceCorp") is False
    assert check_competitor_guard("existingcorp", "SourceCorp") is False
