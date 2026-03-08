import pytest
from unittest.mock import Mock, patch
from openclaw_crm.backends.gspread_backend import GspreadBackend
from openclaw_crm.pipeline import PIPELINE_RANGE

@pytest.fixture
def mock_gspread():
    with patch('openclaw_crm.backends.gspread_backend.gspread') as mock:
        yield mock

@pytest.fixture
def gspread_backend(mock_gspread):
    # Mock the service_account and open_by_key methods
    mock_gspread.service_account.return_value = Mock()
    mock_gspread.service_account.return_value.open_by_key.return_value = Mock()
    
    # Initialize GspreadBackend with a dummy path
    backend = GspreadBackend("dummy_path.json")
    return backend

def test_gspread_read(gspread_backend):
    mock_worksheet = Mock()
    mock_worksheet.get_all_values.return_value = [
        ["Client", "Contact"],
        ["ClientA", "ContactA"],
        ["ClientB", "ContactB"]
    ]
    gspread_backend.gc.open_by_key.return_value.worksheet.return_value = mock_worksheet

    result = gspread_backend.read("spreadsheet_id", PIPELINE_RANGE)
    assert result.success is True
    assert result.data["values"] == [
        ["Client", "Contact"],
        ["ClientA", "ContactA"],
        ["ClientB", "ContactB"]
    ]
    mock_worksheet.get_all_values.assert_called_once()

def test_gspread_append(gspread_backend):
    mock_worksheet = Mock()
    gspread_backend.gc.open_by_key.return_value.worksheet.return_value = mock_worksheet

    values = [["NewClient", "NewContact"]]
    result = gspread_backend.append("spreadsheet_id", PIPELINE_RANGE, values)
    assert result.success is True
    mock_worksheet.append_rows.assert_called_once_with(values, value_input_option='USER_ENTERED')

def test_gspread_update(gspread_backend):
    mock_worksheet = Mock()
    gspread_backend.gc.open_by_key.return_value.worksheet.return_value = mock_worksheet

    values = [["UpdatedClient", "UpdatedContact"]]
    range_to_update = "Pipeline!A2:B2"
    result = gspread_backend.update("spreadsheet_id", range_to_update, values)
    assert result.success is True
    mock_worksheet.update.assert_called_once_with("A2:B2", values, value_input_option='USER_ENTERED')

def test_gspread_init_import_error():
    with patch('openclaw_crm.backends.gspread_backend.gspread', None): # Simulate gspread not installed
        with pytest.raises(ImportError, match="gspread is required for GspreadBackend"):
            GspreadBackend("dummy_path.json")

def test_gspread_init_credentials_error(mock_gspread):
    mock_gspread.service_account.side_effect = Exception("Invalid credentials")
    with pytest.raises(ValueError, match="Failed to load gspread credentials"):
        GspreadBackend("dummy_path.json")
