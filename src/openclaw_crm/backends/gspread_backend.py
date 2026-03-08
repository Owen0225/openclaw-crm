from __future__ import annotations

import json
from typing import Any

try:
    import gspread
except ImportError:
    gspread = None

from openclaw_crm.sheets import SheetsBackend, SheetResult

class GspreadBackend(SheetsBackend):
    def __init__(self, credentials_path: str):
        if gspread is None:
            raise ImportError("gspread is required for GspreadBackend. Install with: pip install gspread")
        try:
            self.gc = gspread.service_account(filename=credentials_path)
        except Exception as e:
            raise ValueError(f"Failed to load gspread credentials from {credentials_path}: {e}")

    def _get_worksheet(self, spreadsheet_id: str, range_: str):
        sh = self.gc.open_by_key(spreadsheet_id)
        # Extract worksheet title from range, e.g., "Pipeline!A:U" -> "Pipeline"
        worksheet_title = range_.split("!")[0].strip("'")
        return sh.worksheet(worksheet_title)

    def read(self, spreadsheet_id: str, range_: str) -> SheetResult:
        try:
            worksheet = self._get_worksheet(spreadsheet_id, range_)
            values = worksheet.get_all_values()
            return SheetResult(success=True, data={"values": values})
        except Exception as e:
            return SheetResult(success=False, data=None, error=str(e))

    def append(self, spreadsheet_id: str, range_: str, values: list[list[str]]) -> SheetResult:
        try:
            worksheet = self._get_worksheet(spreadsheet_id, range_)
            worksheet.append_rows(values, value_input_option='USER_ENTERED')
            return SheetResult(success=True, data={})
        except Exception as e:
            return SheetResult(success=False, data=None, error=str(e))

    def update(self, spreadsheet_id: str, range_: str, values: list[list[str]]) -> SheetResult:
        try:
            worksheet = self._get_worksheet(spreadsheet_id, range_)
            # gspread's update method requires a cell range, not just a sheet range
            # We need to parse the range (e.g. "Pipeline!A2:U2") to get the actual cell range
            # Assuming range_ will always be in A{row}:U{row} format for updates
            
            # Extract actual range (e.g. A2:U2 from 'Pipeline!A2:U2')
            cell_range = range_.split('!', 1)[-1] 

            worksheet.update(cell_range, values, value_input_option='USER_ENTERED')
            return SheetResult(success=True, data={})
        except Exception as e:
            return SheetResult(success=False, data=None, error=str(e))
