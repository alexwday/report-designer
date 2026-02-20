"""
Stock Prices Retriever

Retrieves stock price data for Canadian Big 6 banks.
"""

from ..db import query


# Valid values for documentation
VALID_BANKS = ["RY", "TD", "BMO", "BNS", "CM", "NA"]
VALID_QUARTERS = ["Q1", "Q2", "Q3", "Q4"]

# Bank name mapping
BANK_NAMES = {
    "RY": "Royal Bank of Canada",
    "TD": "Toronto-Dominion Bank",
    "BMO": "Bank of Montreal",
    "BNS": "Bank of Nova Scotia (Scotiabank)",
    "CM": "Canadian Imperial Bank of Commerce (CIBC)",
    "NA": "National Bank of Canada",
}

# TSX tickers
BANK_TICKERS = {
    "RY": "RY.TO",
    "TD": "TD.TO",
    "BMO": "BMO.TO",
    "BNS": "BNS.TO",
    "CM": "CM.TO",
    "NA": "NA.TO",
}


def search_stock_prices(queries: list[dict]) -> list[dict]:
    """
    Retrieve stock price data for specified bank/period combinations.

    Args:
        queries: List of {bank_id, fiscal_year, fiscal_quarter} dicts

    Returns:
        List of results, one per query combination
    """
    results = []

    for q in queries:
        bank_id = q["bank_id"]
        fiscal_year = q["fiscal_year"]
        fiscal_quarter = q["fiscal_quarter"]

        sql = """
            SELECT bank_id, fiscal_year, fiscal_quarter,
                   close_price, qoq_change_pct, yoy_change_pct,
                   period_end_date
            FROM stock_prices
            WHERE bank_id = %s
              AND fiscal_year = %s
              AND fiscal_quarter = %s
        """

        rows = query(sql, (bank_id, fiscal_year, fiscal_quarter))

        if not rows:
            results.append({
                "bank_id": bank_id,
                "bank_name": BANK_NAMES.get(bank_id, bank_id),
                "ticker": BANK_TICKERS.get(bank_id),
                "period": f"{fiscal_year} {fiscal_quarter}",
                "error": "No stock price data found for this period"
            })
            continue

        row = rows[0]
        results.append({
            "bank_id": bank_id,
            "bank_name": BANK_NAMES.get(bank_id, bank_id),
            "ticker": BANK_TICKERS.get(bank_id),
            "period": f"{fiscal_year} {fiscal_quarter}",
            "period_end_date": str(row["period_end_date"]) if row["period_end_date"] else None,
            "close_price": float(row["close_price"]) if row["close_price"] else None,
            "qoq_change_pct": float(row["qoq_change_pct"]) if row["qoq_change_pct"] else None,
            "yoy_change_pct": float(row["yoy_change_pct"]) if row["yoy_change_pct"] else None
        })

    return results


# Tool definition for MCP server
TOOL_DEFINITION = {
    "name": "search_stock_prices",
    "description": """Retrieve stock price data for Canadian Big 6 banks.

BANKS:
- RY: Royal Bank of Canada (RY.TO)
- TD: Toronto-Dominion Bank (TD.TO)
- BMO: Bank of Montreal (BMO.TO)
- BNS: Bank of Nova Scotia (BNS.TO)
- CM: Canadian Imperial Bank of Commerce (CM.TO)
- NA: National Bank of Canada (NA.TO)

DATA RETURNED:
- close_price: End-of-quarter closing price (CAD)
- qoq_change_pct: Quarter-over-quarter percentage change
- yoy_change_pct: Year-over-year percentage change
- period_end_date: Last trading day of the fiscal quarter

PERIODS AVAILABLE:
- Fiscal years: 2024, 2025
- Quarters: Q1, Q2, Q3, Q4
- Note: Canadian banks have Oct 31 fiscal year end (Q1 = Nov-Jan)""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "queries": {
                "type": "array",
                "description": "List of bank/period combinations to query",
                "items": {
                    "type": "object",
                    "properties": {
                        "bank_id": {
                            "type": "string",
                            "enum": VALID_BANKS,
                            "description": "Bank identifier"
                        },
                        "fiscal_year": {
                            "type": "integer",
                            "description": "Fiscal year (2024 or 2025)"
                        },
                        "fiscal_quarter": {
                            "type": "string",
                            "enum": VALID_QUARTERS,
                            "description": "Fiscal quarter"
                        }
                    },
                    "required": ["bank_id", "fiscal_year", "fiscal_quarter"]
                }
            }
        },
        "required": ["queries"]
    }
}
