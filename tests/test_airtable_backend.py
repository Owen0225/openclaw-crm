import pytest
from unittest.mock import Mock, patch
from openclaw_crm.backends.airtable_backend import AirtableBackend, PIPELINE_COLS

@pytest.fixture
def mock_api():
    with patch('openclaw_crm.backends.airtable_backend.Api') as mock:
        yield mock

def test_read_pipeline(mock_api):
    mock_table = Mock()
    mock_table.all.return_value = [
        {"id": "rec123", "fields": {"Client": "Acme", "Stage": "lead", "Budget": "1000"}},
        {"id": "rec456", "fields": {"Client": "Globex", "Stage": "won"}}
    ]
    mock_api.return_value.table.return_value = mock_table

    backend = AirtableBackend("fake_key", "fake_base")
    result = backend.read("fake_spread", "Pipeline!A:U")

    assert result.success is True
    assert len(result.data["values"]) == 3  # Header + 2 rows
    assert result.data["values"][0] == PIPELINE_COLS
    
    # Check row 1 (Acme)
    acme_row = result.data["values"][1]
    assert acme_row[0] == "Acme"
    assert acme_row[3] == "lead"
    assert acme_row[4] == "1000"
    
    # Check row 2 (Globex)
    globex_row = result.data["values"][2]
    assert globex_row[0] == "Globex"
    assert globex_row[3] == "won"
    assert globex_row[4] == ""  # Missing field -> empty string

def test_append_pipeline(mock_api):
    mock_table = Mock()
    mock_table.batch_create.return_value = [{"id": "rec789", "fields": {}}]
    mock_api.return_value.table.return_value = mock_table

    backend = AirtableBackend("fake_key", "fake_base")
    
    values = [
        ["NewCorp", "John Doe", "inbound", "lead", "5000"]
    ]
    
    result = backend.append("fake_spread", "Pipeline!A:U", values)
    
    assert result.success is True
    mock_table.batch_create.assert_called_once()
    created_records = mock_table.batch_create.call_args[0][0]
    
    assert len(created_records) == 1
    assert created_records[0]["Client"] == "NewCorp"
    assert created_records[0]["Contact"] == "John Doe"
    assert created_records[0]["Stage"] == "lead"

def test_update_pipeline(mock_api):
    mock_table = Mock()
    mock_table.all.return_value = [
        {"id": "rec123", "fields": {"Client": "Acme", "Stage": "lead"}}
    ]
    mock_api.return_value.table.return_value = mock_table

    backend = AirtableBackend("fake_key", "fake_base")
    
    # Must read first to populate cache
    backend.read("fake_spread", "Pipeline!A:U")
    
    # Update row 2 (index 1 in cache, which is rec123)
    # Acme row + changing stage to won
    update_row = ["Acme", "", "", "won", "1000"]
    result = backend.update("fake_spread", "Pipeline!A2:U2", [update_row])
    
    assert result.success is True
    mock_table.update.assert_called_once_with("rec123", {
        "Client": "Acme",
        "Contact": "",
        "Source": "",
        "Stage": "won",
        "Budget": "1000"
    })
