"""
Transcripts Retriever

Retrieves earnings call transcript sections for Canadian Big 6 banks.
"""

from typing import Literal
from ..db import query


# Valid values for documentation
VALID_BANKS = ["RY", "TD", "BMO", "BNS", "CM", "NA"]
VALID_QUARTERS = ["Q1", "Q2", "Q3", "Q4"]
VALID_SECTIONS = ["management_discussion", "qa", "both"]

# Bank name mapping for output
BANK_NAMES = {
    "RY": "Royal Bank of Canada",
    "TD": "Toronto-Dominion Bank",
    "BMO": "Bank of Montreal",
    "BNS": "Bank of Nova Scotia (Scotiabank)",
    "CM": "Canadian Imperial Bank of Commerce (CIBC)",
    "NA": "National Bank of Canada",
}


def search_transcripts(
    queries: list[dict],
    section: Literal["management_discussion", "qa", "both"] = "both"
) -> list[dict]:
    """
    Retrieve transcript sections for specified bank/period combinations.

    Args:
        queries: List of {bank_id, fiscal_year, fiscal_quarter} dicts
        section: Which section to retrieve:
            - "management_discussion": CEO/CFO prepared remarks
            - "qa": Analyst Q&A session
            - "both": Full transcript (both sections)

    Returns:
        List of results, one per query combination
    """
    results = []

    for q in queries:
        bank_id = q["bank_id"]
        fiscal_year = q["fiscal_year"]
        fiscal_quarter = q["fiscal_quarter"]

        # Build section filter
        if section == "both":
            section_filter = "1=1"  # No filter
            params = (bank_id, fiscal_year, fiscal_quarter)
        else:
            section_filter = "section = %s"
            params = (bank_id, fiscal_year, fiscal_quarter, section)

        sql = f"""
            SELECT bank_id, fiscal_year, fiscal_quarter, section,
                   content_text, call_date
            FROM transcripts
            WHERE bank_id = %s
              AND fiscal_year = %s
              AND fiscal_quarter = %s
              AND {section_filter}
            ORDER BY section
        """

        rows = query(sql, params)

        if not rows:
            results.append({
                "bank_id": bank_id,
                "bank_name": BANK_NAMES.get(bank_id, bank_id),
                "period": f"{fiscal_year} {fiscal_quarter}",
                "error": "No transcript found for this period"
            })
            continue

        # Combine sections if multiple
        if len(rows) == 1:
            row = rows[0]
            results.append({
                "bank_id": bank_id,
                "bank_name": BANK_NAMES.get(bank_id, bank_id),
                "period": f"{fiscal_year} {fiscal_quarter}",
                "call_date": str(row["call_date"]) if row["call_date"] else None,
                "section": row["section"],
                "content": row["content_text"],
                "content_length": len(row["content_text"])
            })
        else:
            # Multiple sections (both requested)
            sections_data = {}
            call_date = None
            for row in rows:
                sections_data[row["section"]] = row["content_text"]
                if row["call_date"]:
                    call_date = str(row["call_date"])

            results.append({
                "bank_id": bank_id,
                "bank_name": BANK_NAMES.get(bank_id, bank_id),
                "period": f"{fiscal_year} {fiscal_quarter}",
                "call_date": call_date,
                "section": "both",
                "management_discussion": sections_data.get("management_discussion", ""),
                "qa": sections_data.get("qa", ""),
                "content_length": sum(len(v) for v in sections_data.values())
            })

    return results


# Tool definition for MCP server
TOOL_DEFINITION = {
    "name": "search_transcripts",
    "description": """Retrieve earnings call transcript sections for Canadian Big 6 banks.

BANKS:
- RY: Royal Bank of Canada
- TD: Toronto-Dominion Bank
- BMO: Bank of Montreal
- BNS: Bank of Nova Scotia (Scotiabank)
- CM: Canadian Imperial Bank of Commerce (CIBC)
- NA: National Bank of Canada

SECTIONS:
- management_discussion: CEO/CFO prepared remarks about quarterly performance, strategy, and outlook
- qa: Analyst questions and management responses
- both: Full transcript with both sections

PERIODS AVAILABLE:
- Fiscal years: 2024, 2025
- Quarters: Q1, Q2, Q3, Q4
- Note: Canadian banks have Oct 31 fiscal year end (Q1 = Nov-Jan)

Returns full transcript text for each bank/period combination.""",
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
            "section": {
                "type": "string",
                "enum": VALID_SECTIONS,
                "default": "both",
                "description": "Which transcript section to retrieve"
            }
        },
        "required": ["queries"]
    }
}
