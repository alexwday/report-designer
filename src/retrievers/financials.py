"""
Financials Retriever

Retrieves financial metrics for Canadian Big 6 banks.
"""

from ..db import query


# Valid values for documentation
VALID_BANKS = ["RY", "TD", "BMO", "BNS", "CM", "NA"]
VALID_QUARTERS = ["Q1", "Q2", "Q3", "Q4"]

# All 25 available metrics
AVAILABLE_METRICS = [
    # Profitability
    {"id": "total_revenue", "name": "Total Revenue", "category": "profitability"},
    {"id": "net_income", "name": "Net Income", "category": "profitability"},
    {"id": "diluted_eps", "name": "Diluted EPS", "category": "profitability"},
    {"id": "roe", "name": "Return on Equity", "category": "profitability"},
    {"id": "roa", "name": "Return on Assets", "category": "profitability"},
    # Capital
    {"id": "cet1_ratio", "name": "CET1 Ratio", "category": "capital"},
    {"id": "tier1_ratio", "name": "Tier 1 Capital Ratio", "category": "capital"},
    {"id": "total_capital_ratio", "name": "Total Capital Ratio", "category": "capital"},
    {"id": "book_value_per_share", "name": "Book Value per Share", "category": "capital"},
    # Efficiency
    {"id": "nim", "name": "Net Interest Margin", "category": "efficiency"},
    {"id": "efficiency_ratio", "name": "Efficiency Ratio", "category": "efficiency"},
    {"id": "operating_leverage", "name": "Operating Leverage", "category": "efficiency"},
    {"id": "net_interest_income", "name": "Net Interest Income", "category": "efficiency"},
    # Credit
    {"id": "pcl", "name": "Provision for Credit Losses", "category": "credit"},
    {"id": "pcl_ratio", "name": "PCL Ratio", "category": "credit"},
    {"id": "gross_impaired_loans", "name": "Gross Impaired Loans", "category": "credit"},
    {"id": "gil_ratio", "name": "Gross Impaired Loan Ratio", "category": "credit"},
    # Balance Sheet
    {"id": "total_assets", "name": "Total Assets", "category": "balance_sheet"},
    {"id": "total_loans", "name": "Total Loans", "category": "balance_sheet"},
    {"id": "total_deposits", "name": "Total Deposits", "category": "balance_sheet"},
    {"id": "loan_to_deposit_ratio", "name": "Loan-to-Deposit Ratio", "category": "balance_sheet"},
    {"id": "common_equity", "name": "Common Equity", "category": "balance_sheet"},
    # Other
    {"id": "non_interest_revenue", "name": "Non-Interest Revenue", "category": "other"},
    {"id": "aum", "name": "Assets Under Management", "category": "other"},
    {"id": "dividend_per_share", "name": "Dividend per Share", "category": "other"},
]

METRIC_IDS = [m["id"] for m in AVAILABLE_METRICS]

# Bank name mapping
BANK_NAMES = {
    "RY": "Royal Bank of Canada",
    "TD": "Toronto-Dominion Bank",
    "BMO": "Bank of Montreal",
    "BNS": "Bank of Nova Scotia (Scotiabank)",
    "CM": "Canadian Imperial Bank of Commerce (CIBC)",
    "NA": "National Bank of Canada",
}


def search_financials(
    queries: list[dict],
    metrics: list[str] = None
) -> list[dict]:
    """
    Retrieve financial metrics for specified bank/period combinations.

    Args:
        queries: List of {bank_id, fiscal_year, fiscal_quarter} dicts
        metrics: List of metric IDs to retrieve (default: all 25)

    Returns:
        List of results, one per query combination
    """
    # Default to all metrics if not specified
    if metrics is None:
        metrics = METRIC_IDS

    results = []

    for q in queries:
        bank_id = q["bank_id"]
        fiscal_year = q["fiscal_year"]
        fiscal_quarter = q["fiscal_quarter"]

        # Build metric filter
        placeholders = ",".join(["%s"] * len(metrics))
        params = (bank_id, fiscal_year, fiscal_quarter) + tuple(metrics)

        sql = f"""
            SELECT metric_id, metric_name, value, unit, formatted_value
            FROM financials
            WHERE bank_id = %s
              AND fiscal_year = %s
              AND fiscal_quarter = %s
              AND metric_id IN ({placeholders})
            ORDER BY metric_id
        """

        rows = query(sql, params)

        if not rows:
            results.append({
                "bank_id": bank_id,
                "bank_name": BANK_NAMES.get(bank_id, bank_id),
                "period": f"{fiscal_year} {fiscal_quarter}",
                "error": "No financial data found for this period"
            })
            continue

        # Format metrics
        metrics_data = []
        for row in rows:
            metrics_data.append({
                "id": row["metric_id"],
                "name": row["metric_name"],
                "value": float(row["value"]) if row["value"] is not None else None,
                "unit": row["unit"],
                "formatted": row["formatted_value"]
            })

        results.append({
            "bank_id": bank_id,
            "bank_name": BANK_NAMES.get(bank_id, bank_id),
            "period": f"{fiscal_year} {fiscal_quarter}",
            "metrics_count": len(metrics_data),
            "metrics": metrics_data
        })

    return results


# Build metric list for documentation
def _format_metrics_doc():
    lines = []
    current_category = None
    for m in AVAILABLE_METRICS:
        if m["category"] != current_category:
            current_category = m["category"]
            lines.append(f"\n{current_category.upper()}:")
        lines.append(f"  - {m['id']}: {m['name']}")
    return "\n".join(lines)


# Tool definition for MCP server
TOOL_DEFINITION = {
    "name": "search_financials",
    "description": f"""Retrieve financial metrics for Canadian Big 6 banks.

BANKS:
- RY: Royal Bank of Canada
- TD: Toronto-Dominion Bank
- BMO: Bank of Montreal
- BNS: Bank of Nova Scotia (Scotiabank)
- CM: Canadian Imperial Bank of Commerce (CIBC)
- NA: National Bank of Canada

AVAILABLE METRICS (25 total):
{_format_metrics_doc()}

PERIODS AVAILABLE:
- Fiscal years: 2024, 2025
- Quarters: Q1, Q2, Q3, Q4
- Note: Canadian banks have Oct 31 fiscal year end (Q1 = Nov-Jan)

Returns numeric values and formatted strings for each metric.""",
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
            },
            "metrics": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": METRIC_IDS
                },
                "description": "List of metric IDs to retrieve. Omit for all 25 metrics."
            }
        },
        "required": ["queries"]
    }
}
