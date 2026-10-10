"""Read the original UCI 350 XLS workbook without changing its bytes."""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from credit_risk.data.schema import NORMALIZED_COLUMNS, SOURCE_COLUMNS, DataContractError


@dataclass(frozen=True)
class WorkbookLoad:
    records: list[dict[str, Any]]
    metadata: dict[str, Any]
    sha256: str


def load_workbook(path: str | Path) -> WorkbookLoad:
    """Require the released ``Data`` sheet, alias row, and exact header row.

    xlrd is imported only here so fixture-based validation and features do not
    need a workbook reader. Blank cells are represented as None; text/error/date
    cells are retained as nonnumeric values for row validation to quarantine.
    """
    import xlrd

    path = Path(path)
    content = path.read_bytes()
    checksum = hashlib.sha256(content).hexdigest()
    book = xlrd.open_workbook(file_contents=content, on_demand=True)
    try:
        if "Data" not in book.sheet_names():
            raise DataContractError("Expected the original workbook's 'Data' sheet")
        sheet = book.sheet_by_name("Data")
        if sheet.ncols != len(SOURCE_COLUMNS) or sheet.nrows < 3:
            raise DataContractError("Unexpected workbook dimensions or missing data rows")
        actual_header = tuple(sheet.row_values(1))
        if actual_header != SOURCE_COLUMNS:
            raise DataContractError(f"Unexpected workbook header: {actual_header!r}")
        alias_row = tuple(sheet.row_values(0))
        expected_aliases = ("", *(f"X{i}" for i in range(1, 24)), "Y")
        if alias_row != expected_aliases:
            raise DataContractError(f"Unexpected workbook variable-code row: {alias_row!r}")
        records = []
        cell_types: Counter[str] = Counter()
        for row_index in range(2, sheet.nrows):
            record = {}
            for column_index, column in enumerate(NORMALIZED_COLUMNS):
                cell = sheet.cell(row_index, column_index)
                cell_types[str(cell.ctype)] += 1
                if cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                    value = None
                elif cell.ctype == xlrd.XL_CELL_NUMBER:
                    value = cell.value
                else:
                    # Preserve cell type in an invalid value, rather than
                    # accidentally accepting Excel boolean/error codes as ints.
                    value = {"excel_cell_type": cell.ctype, "value": cell.value}
                record[column] = value
            records.append(record)
        metadata = {
            "file_name": path.name,
            "byte_count": len(content),
            "reader": "xlrd",
            "reader_version": xlrd.__version__,
            "sheet_names": book.sheet_names(),
            "selected_sheet": sheet.name,
            "sheet_rows_including_headers": sheet.nrows,
            "sheet_columns": sheet.ncols,
            "header_row_zero_based": 1,
            "header_row_excel": 2,
            "variable_code_row_zero_based": 0,
            "data_start_row_excel": 3,
            "source_header": list(actual_header),
            "variable_codes": list(alias_row),
            "normalized_columns": list(NORMALIZED_COLUMNS),
            "data_rows": len(records),
            "data_cell_types": dict(sorted(cell_types.items())),
            "cell_type_codes": {
                "0": "empty", "1": "text", "2": "number", "3": "date",
                "4": "boolean", "5": "error", "6": "blank",
            },
        }
        return WorkbookLoad(records, metadata, checksum)
    finally:
        book.release_resources()
