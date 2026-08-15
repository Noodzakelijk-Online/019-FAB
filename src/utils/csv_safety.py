from typing import Any, Mapping


CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")


def neutralize_csv_cell(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(CSV_FORMULA_PREFIXES):
        return f"'{value}"
    return value


def neutralize_csv_row(row: Mapping[Any, Any]) -> dict:
    return {key: neutralize_csv_cell(value) for key, value in row.items()}
