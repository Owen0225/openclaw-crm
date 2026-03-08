import pytest
from datetime import date, timedelta
from openclaw_crm.pipeline import (
    get_pipeline, create_deal, move_stage, 
    get_pipeline_summary, get_stale_deals,
    HEADERS, PIPELINE_RANGE
)
import os

@pytest.fixture(autouse=True)
def setup_env():
    os.environ["CRM_SPREADSHEET_ID"] = "test_id"
    yield
    if "CRM_SPREADSHEET_ID" in os.environ:
        del os.environ["CRM_SPREADSHEET_ID"]

def test_empty_pipeline():
    deals = get_pipeline()
    assert len(deals) == 0

def test_create_deal(mock_sheets_backend):
    deal_data = {
        "client": "TestCorp",
        "budget": "5000",
        "stage": "lead",
        "source": "inbound"
    }
    res = create_deal(deal_data)
    assert res["ok"] is True
    assert res["client"] == "TestCorp"
    
    # Verify in backend
    rows = mock_sheets_backend.data[PIPELINE_RANGE]
    assert len(rows) == 2  # header + 1 deal
    assert rows[1][0] == "TestCorp"
    assert rows[1][3] == "lead"
    assert rows[1][4] == "5000"

def test_get_pipeline(mock_sheets_backend):
    create_deal({"client": "Active1", "stage": "lead"})
    create_deal({"client": "Active2", "stage": "proposal"})
    create_deal({"client": "ClosedWon", "stage": "won"})
    create_deal({"client": "ClosedLost", "stage": "lost"})
    
    active_deals = get_pipeline(active_only=True)
    assert len(active_deals) == 2
    assert active_deals[0]["Client"] == "Active1"
    
    all_deals = get_pipeline(active_only=False)
    assert len(all_deals) == 4

def test_move_stage(mock_sheets_backend):
    create_deal({"client": "MoveMe", "stage": "lead"})
    
    res = move_stage("MoveMe", "proposal")
    assert res["ok"] is True
    assert res["stage"] == "proposal"
    
    deals = get_pipeline()
    assert len(deals) == 1
    assert deals[0]["Stage"] == "proposal"
    assert deals[0]["Last Contact"] == date.today().isoformat()

def test_get_pipeline_summary(mock_sheets_backend):
    create_deal({"client": "A", "stage": "proposal", "budget": "1000"}) # 50% = 500
    create_deal({"client": "B", "stage": "lead", "budget": "2000"})     # 10% = 200
    create_deal({"client": "C", "stage": "won", "budget": "5000"})      # inactive
    
    summary = get_pipeline_summary()
    assert summary["total_deals"] == 2
    assert summary["won_deals"] == 1
    assert summary["total_weighted_value"] == 700.0
    assert summary["by_stage"]["proposal"] == 1
    assert summary["by_stage"]["lead"] == 1

def test_get_stale_deals(mock_sheets_backend):
    # Need to manually inject dates for testing staleness
    old_date = (date.today() - timedelta(days=10)).isoformat()
    
    row1 = ["Stale Deal", "", "upwork", "lead", "100", "fixed", "", old_date, old_date] + [""] * 12
    row2 = ["Fresh Deal", "", "upwork", "lead", "100", "fixed", "", date.today().isoformat(), date.today().isoformat()] + [""] * 12
    
    mock_sheets_backend.data[PIPELINE_RANGE].append(row1)
    mock_sheets_backend.data[PIPELINE_RANGE].append(row2)
    
    stale = get_stale_deals([7, 14])
    assert len(stale[7]) == 1
    assert stale[7][0]["Client"] == "Stale Deal"
    assert len(stale[14]) == 0
