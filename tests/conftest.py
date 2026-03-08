import pytest
import re
from openclaw_crm.sheets import SheetsBackend, SheetResult, set_backend

class MockBackend(SheetsBackend):
    def __init__(self):
        self.data = {
            "Pipeline!A:U": [
                [
                    "Client", "Contact", "Source", "Stage", "Budget", "Rate Type",
                    "Service", "First Contact", "Last Contact", "Next Action",
                    "Due Date", "Notes", "Slack Channel", "Proposal Link",
                    "Owner", "Upwork URL", "Probability", "Referred By",
                    "Network Parent", "Network Notes", "Signal Date"
                ]
            ],
            "'Network Signals'!A:F": [
                [
                    "Timestamp", "Source Client", "Channel", "Signal Text",
                    "Mentioned Company", "Status"
                ]
            ],
            "Clients!A:I": [
                [
                    "Client", "Status", "Contact", "Email", "Phone",
                    "Address", "Website", "Notes", "Created"
                ]
            ],
            "'Revenue Log'!A:F": [
                [
                    "Invoice ID", "Client", "Amount", "Date", "Status", "Notes"
                ]
            ]
        }

    def _get_table_key(self, range_):
        if "Pipeline" in range_:
            return "Pipeline!A:U"
        if "Signals" in range_:
            return "'Network Signals'!A:F"
        if "Clients" in range_:
            return "Clients!A:I"
        if "Revenue" in range_:
            return "'Revenue Log'!A:F"
        return range_

    def read(self, spreadsheet_id, range_):
        key = self._get_table_key(range_)
        if key not in self.data:
            return SheetResult(success=True, data={"values": []})
        
        # Deep copy to prevent accidental mutation of mock state
        values = [row[:] for row in self.data[key]]
        return SheetResult(success=True, data={"values": values})

    def append(self, spreadsheet_id, range_, values):
        key = self._get_table_key(range_)
        if key not in self.data:
            self.data[key] = []
        for row in values:
            self.data[key].append(row)
        return SheetResult(success=True, data={})

    def update(self, spreadsheet_id, range_, values):
        key = self._get_table_key(range_)
        match = re.search(r'!A(\d+)', range_)
        if not match:
            return SheetResult(success=False, data=None, error="Invalid range")
        
        row_idx = int(match.group(1)) - 1
        if key not in self.data or row_idx >= len(self.data[key]):
            return SheetResult(success=False, data=None, error="Row out of range")
            
        # Update row logic
        current_row = self.data[key][row_idx]
        new_row = values[0]
        
        for i, val in enumerate(new_row):
            if i < len(current_row):
                current_row[i] = val
            else:
                current_row.append(val)
                
        return SheetResult(success=True, data={})


@pytest.fixture(autouse=True)
def mock_sheets_backend():
    backend = MockBackend()
    set_backend(backend)
    return backend
