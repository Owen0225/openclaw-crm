from __future__ import annotations

import re
from typing import Any

try:
    from pyairtable import Api
except ImportError:
    Api = None

from openclaw_crm.sheets import SheetsBackend, SheetResult

PIPELINE_COLS = [
    "Client", "Contact", "Source", "Stage", "Budget", "Rate Type", "Service",
    "First Contact", "Last Contact", "Next Action", "Due Date", "Notes",
    "Slack Channel", "Proposal Link", "Owner", "Upwork URL", "Probability",
    "Referred By", "Network Parent", "Network Notes", "Signal Date"
]

SIGNALS_COLS = [
    "Timestamp", "Source Client", "Channel", "Signal Text", "Mentioned Company", "Status"
]

class AirtableBackend(SheetsBackend):
    def __init__(self, api_key: str, base_id: str):
        if Api is None:
            raise ImportError("pyairtable is required for AirtableBackend. Install with: pip install pyairtable")
        self.api = Api(api_key)
        self.base_id = base_id
        self._record_map: dict[str, list[str | None]] = {}

    def _get_table_name(self, range_: str) -> str:
        return range_.split("!")[0].strip("'")

    def _get_cols(self, table_name: str) -> list[str]:
        if "Pipeline" in table_name:
            return PIPELINE_COLS
        elif "Signal" in table_name:
            return SIGNALS_COLS
        return PIPELINE_COLS

    def read(self, spreadsheet_id: str, range_: str) -> SheetResult:
        try:
            table_name = self._get_table_name(range_)
            table = self.api.table(self.base_id, table_name)
            records = table.all()

            cols = self._get_cols(table_name)
            
            values = [cols] # Row 1 is header
            record_ids: list[str | None] = [None] # Index 0 is header, so no record ID
            
            for rec in records:
                fields = rec.get("fields", {})
                row = [str(fields.get(c, "")) for c in cols]
                values.append(row)
                record_ids.append(rec["id"])
                
            self._record_map[table_name] = record_ids
            return SheetResult(success=True, data={"values": values})
        except Exception as e:
            return SheetResult(success=False, data=None, error=str(e))

    def append(self, spreadsheet_id: str, range_: str, values: list[list[str]]) -> SheetResult:
        try:
            table_name = self._get_table_name(range_)
            table = self.api.table(self.base_id, table_name)
            cols = self._get_cols(table_name)

            records_to_create = []
            for row in values:
                fields = {}
                for i, val in enumerate(row):
                    if i < len(cols) and val:
                        fields[cols[i]] = val
                records_to_create.append(fields)

            created = table.batch_create(records_to_create)
            
            # update cache if needed, though usually read() is called again
            if table_name in self._record_map:
                for rec in created:
                    self._record_map[table_name].append(rec["id"])

            return SheetResult(success=True, data={})
        except Exception as e:
            return SheetResult(success=False, data=None, error=str(e))

    def update(self, spreadsheet_id: str, range_: str, values: list[list[str]]) -> SheetResult:
        try:
            table_name = self._get_table_name(range_)
            table = self.api.table(self.base_id, table_name)
            cols = self._get_cols(table_name)

            match = re.search(r'!A(\d+):', range_)
            if not match:
                match = re.search(r'!A(\d+)', range_)
                
            if not match:
                return SheetResult(success=False, data=None, error=f"Could not parse row from range {range_}")
                
            row_num = int(match.group(1))
            
            if table_name not in self._record_map or row_num - 1 >= len(self._record_map[table_name]):
                return SheetResult(success=False, data=None, error="Record ID not found in cache. Call read() first.")
                
            record_id = self._record_map[table_name][row_num - 1]
            if not record_id:
                 return SheetResult(success=False, data=None, error="Invalid record ID mapping.")

            fields = {}
            row = values[0]
            for i, val in enumerate(row):
                if i < len(cols):
                    # In Airtable, sending empty string might be fine or we could use None.
                    # String values are expected based on sheet conversion.
                    fields[cols[i]] = val

            table.update(record_id, fields)
            return SheetResult(success=True, data={})
        except Exception as e:
            return SheetResult(success=False, data=None, error=str(e))
