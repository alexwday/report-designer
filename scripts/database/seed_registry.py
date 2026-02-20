"""
Seed the data_source_registry with existing data sources.

Run from project root: python scripts/database/seed_registry.py
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.db import get_connection


DATA_SOURCES = [
    {
        "id": "transcripts",
        "name": "Earnings Call Transcripts",
        "description": """Earnings call transcript sections for Canadian Big 6 banks.

AVAILABLE BANKS:
- RY: Royal Bank of Canada
- TD: Toronto-Dominion Bank
- BMO: Bank of Montreal
- BNS: Bank of Nova Scotia (Scotiabank)
- CM: Canadian Imperial Bank of Commerce (CIBC)
- NA: National Bank of Canada

AVAILABLE SECTIONS:
- management_discussion: Prepared remarks from executives
- qa: Analyst Q&A session

PERIODS AVAILABLE:
- Fiscal years: 2024, 2025
- Quarters: Q1, Q2, Q3, Q4
- Note: Canadian banks have Oct 31 fiscal year end (Q1 = Nov-Jan)""",
        "category": "bank_data",
        "retrieval_methods": [
            {
                "method_id": "by_quarter",
                "name": "By Quarter",
                "description": "Get transcript section for a specific bank/quarter",
                "mcp_tool": "search_transcripts",
                "parameters": [
                    {"key": "bank_id", "type": "enum", "options": ["RY", "TD", "BMO", "BNS", "CM", "NA"], "required": True, "prompt": "Which bank?"},
                    {"key": "fiscal_year", "type": "integer", "required": True, "prompt": "Which fiscal year?"},
                    {"key": "fiscal_quarter", "type": "enum", "options": ["Q1", "Q2", "Q3", "Q4"], "required": True, "prompt": "Which quarter?"},
                    {"key": "section", "type": "enum", "options": ["management_discussion", "qa", "both"], "required": False, "default": "both", "prompt": "Which section?"}
                ],
                "returns": "Full transcript section text with metadata"
            },
            {
                "method_id": "compare_banks",
                "name": "Compare Banks",
                "description": "Get transcripts for multiple banks in the same quarter",
                "mcp_tool": "search_transcripts",
                "parameters": [
                    {"key": "bank_ids", "type": "array", "items": {"type": "enum", "options": ["RY", "TD", "BMO", "BNS", "CM", "NA"]}, "required": True, "prompt": "Which banks to compare?"},
                    {"key": "fiscal_year", "type": "integer", "required": True, "prompt": "Which fiscal year?"},
                    {"key": "fiscal_quarter", "type": "enum", "options": ["Q1", "Q2", "Q3", "Q4"], "required": True, "prompt": "Which quarter?"},
                    {"key": "section", "type": "enum", "options": ["management_discussion", "qa", "both"], "required": False, "default": "both"}
                ],
                "returns": "Transcripts for each bank"
            }
        ],
        "suggested_widgets": ["summary", "key_points", "comparison", "custom"]
    },
    {
        "id": "financials",
        "name": "Financial Metrics",
        "description": """Top 25 financial metrics for Canadian Big 6 banks.

AVAILABLE BANKS:
- RY: Royal Bank of Canada
- TD: Toronto-Dominion Bank
- BMO: Bank of Montreal
- BNS: Bank of Nova Scotia (Scotiabank)
- CM: Canadian Imperial Bank of Commerce (CIBC)
- NA: National Bank of Canada

AVAILABLE METRICS (25 total):

PROFITABILITY:
- total_revenue, net_income, diluted_eps, roe, roa

CAPITAL:
- cet1_ratio, tier1_ratio, total_capital_ratio, book_value_per_share

EFFICIENCY:
- nim, efficiency_ratio, operating_leverage, net_interest_income

CREDIT:
- pcl, pcl_ratio, gross_impaired_loans, gil_ratio

BALANCE SHEET:
- total_assets, total_loans, total_deposits, loan_to_deposit_ratio, common_equity

OTHER:
- non_interest_revenue, aum, dividend_per_share

PERIODS AVAILABLE:
- Fiscal years: 2024, 2025
- Quarters: Q1, Q2, Q3, Q4""",
        "category": "bank_data",
        "retrieval_methods": [
            {
                "method_id": "by_quarter",
                "name": "By Quarter",
                "description": "Get financial metrics for a specific bank/quarter",
                "mcp_tool": "search_financials",
                "parameters": [
                    {"key": "bank_id", "type": "enum", "options": ["RY", "TD", "BMO", "BNS", "CM", "NA"], "required": True, "prompt": "Which bank?"},
                    {"key": "fiscal_year", "type": "integer", "required": True, "prompt": "Which fiscal year?"},
                    {"key": "fiscal_quarter", "type": "enum", "options": ["Q1", "Q2", "Q3", "Q4"], "required": True, "prompt": "Which quarter?"},
                    {"key": "metrics", "type": "array", "items": {"type": "string"}, "required": False, "prompt": "Which metrics? (leave empty for all 25)"}
                ],
                "returns": "Metric values with formatted display strings"
            },
            {
                "method_id": "compare_banks",
                "name": "Compare Banks",
                "description": "Compare financial metrics across multiple banks",
                "mcp_tool": "search_financials",
                "parameters": [
                    {"key": "bank_ids", "type": "array", "items": {"type": "enum", "options": ["RY", "TD", "BMO", "BNS", "CM", "NA"]}, "required": True, "prompt": "Which banks to compare?"},
                    {"key": "fiscal_year", "type": "integer", "required": True, "prompt": "Which fiscal year?"},
                    {"key": "fiscal_quarter", "type": "enum", "options": ["Q1", "Q2", "Q3", "Q4"], "required": True, "prompt": "Which quarter?"},
                    {"key": "metrics", "type": "array", "items": {"type": "string"}, "required": False}
                ],
                "returns": "Metrics for each bank for comparison"
            }
        ],
        "suggested_widgets": ["table", "comparison", "chart", "key_points"]
    },
    {
        "id": "stock_prices",
        "name": "Stock Prices",
        "description": """End-of-quarter stock prices with period-over-period changes for Canadian Big 6 banks.

AVAILABLE BANKS:
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
- Quarters: Q1, Q2, Q3, Q4""",
        "category": "bank_data",
        "retrieval_methods": [
            {
                "method_id": "by_quarter",
                "name": "By Quarter",
                "description": "Get stock price for a specific bank/quarter",
                "mcp_tool": "search_stock_prices",
                "parameters": [
                    {"key": "bank_id", "type": "enum", "options": ["RY", "TD", "BMO", "BNS", "CM", "NA"], "required": True, "prompt": "Which bank?"},
                    {"key": "fiscal_year", "type": "integer", "required": True, "prompt": "Which fiscal year?"},
                    {"key": "fiscal_quarter", "type": "enum", "options": ["Q1", "Q2", "Q3", "Q4"], "required": True, "prompt": "Which quarter?"}
                ],
                "returns": "Stock price with QoQ and YoY changes"
            },
            {
                "method_id": "compare_banks",
                "name": "Compare Banks",
                "description": "Compare stock performance across multiple banks",
                "mcp_tool": "search_stock_prices",
                "parameters": [
                    {"key": "bank_ids", "type": "array", "items": {"type": "enum", "options": ["RY", "TD", "BMO", "BNS", "CM", "NA"]}, "required": True, "prompt": "Which banks to compare?"},
                    {"key": "fiscal_year", "type": "integer", "required": True, "prompt": "Which fiscal year?"},
                    {"key": "fiscal_quarter", "type": "enum", "options": ["Q1", "Q2", "Q3", "Q4"], "required": True, "prompt": "Which quarter?"}
                ],
                "returns": "Stock prices for each bank"
            },
            {
                "method_id": "trend",
                "name": "Price Trend",
                "description": "Get stock price trend over multiple quarters",
                "mcp_tool": "search_stock_prices",
                "parameters": [
                    {"key": "bank_id", "type": "enum", "options": ["RY", "TD", "BMO", "BNS", "CM", "NA"], "required": True, "prompt": "Which bank?"},
                    {"key": "periods", "type": "array", "items": {"type": "object", "properties": {"fiscal_year": {"type": "integer"}, "fiscal_quarter": {"type": "string"}}}, "required": True, "prompt": "Which periods?"}
                ],
                "returns": "Stock prices across specified periods"
            }
        ],
        "suggested_widgets": ["table", "chart", "comparison"]
    }
]


def seed_registry():
    """Seed the data_source_registry table."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for source in DATA_SOURCES:
                cur.execute("""
                    INSERT INTO data_source_registry (id, name, description, category, retrieval_methods, suggested_widgets)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        category = EXCLUDED.category,
                        retrieval_methods = EXCLUDED.retrieval_methods,
                        suggested_widgets = EXCLUDED.suggested_widgets,
                        updated_at = NOW()
                """, (
                    source["id"],
                    source["name"],
                    source["description"],
                    source["category"],
                    json.dumps(source["retrieval_methods"]),
                    json.dumps(source["suggested_widgets"])
                ))
                print(f"  Seeded: {source['id']}")

            conn.commit()
            print(f"\nSeeded {len(DATA_SOURCES)} data sources")

    finally:
        conn.close()


def verify_registry():
    """Verify the registry was seeded correctly."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, category FROM data_source_registry ORDER BY id")
            rows = cur.fetchall()
            print("\nData Source Registry:")
            print("-" * 50)
            for row in rows:
                print(f"  {row[0]}: {row[1]} ({row[2]})")
    finally:
        conn.close()


if __name__ == "__main__":
    print("Seeding data_source_registry...")
    seed_registry()
    verify_registry()
