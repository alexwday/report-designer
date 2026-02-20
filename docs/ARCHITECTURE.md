# Report Designer - Architecture

## Overview

LLM-powered document generation tool that retrieves financial data for Canadian banks and generates reports. Uses MCP (Model Context Protocol) to expose data retrievers as tools that an LLM agent can call.

## Companies

The Big 6 Canadian Banks:

| Bank ID | Name | Ticker | Fiscal Year End |
|---------|------|--------|-----------------|
| RY | Royal Bank of Canada | RY | October 31 |
| TD | Toronto-Dominion Bank | TD | October 31 |
| BMO | Bank of Montreal | BMO | October 31 |
| BNS | Bank of Nova Scotia (Scotiabank) | BNS | October 31 |
| CM | Canadian Imperial Bank of Commerce | CM | October 31 |
| NA | National Bank of Canada | NA | October 31 |

Note: Canadian banks have fiscal years ending October 31, so Q1 = Nov-Jan, Q2 = Feb-Apr, Q3 = May-Jul, Q4 = Aug-Oct.

## Data Sources

### 1. Transcripts

Earnings call transcripts with two sections per call.

**Table: `transcripts`**

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | Unique identifier |
| bank_id | TEXT | Bank identifier (RY, TD, BMO, BNS, CM, NA) |
| fiscal_year | INTEGER | Fiscal year (2025) |
| fiscal_quarter | TEXT | Quarter (Q1, Q2, Q3, Q4) |
| section | TEXT | Section type (management_discussion, qa) |
| content_text | TEXT | Full section text |
| call_date | DATE | Date of earnings call |
| created_at | TIMESTAMP | Record creation time |

**Filters:**
- `bank_id`: Which bank
- `fiscal_year`: Which year
- `fiscal_quarter`: Which quarter
- `section`: management_discussion (executive prepared remarks) or qa (analyst Q&A)

**Content:** Full section text. Agent retrieves entire section.

---

### 2. Financials

Top 25 financial metrics shared across all banks.

**Table: `financials`**

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | Unique identifier |
| bank_id | TEXT | Bank identifier |
| fiscal_year | INTEGER | Fiscal year |
| fiscal_quarter | TEXT | Quarter (Q1, Q2, Q3, Q4) |
| metric_id | TEXT | Metric identifier |
| metric_name | TEXT | Human-readable metric name |
| value | DECIMAL | Numeric value |
| unit | TEXT | Unit (CAD, percent, ratio, bps) |
| formatted_value | TEXT | Display-formatted value ($1.2B) |
| created_at | TIMESTAMP | Record creation time |

**Filters:**
- `bank_id`: Which bank
- `fiscal_year`: Which year
- `fiscal_quarter`: Which quarter
- `metric_id`: Which metric

**Structure:** One row per metric per bank per period.

**Metrics (25 total):** TBD - will be determined based on what's consistently available across all 6 banks in their supplementary packages.

---

### 3. Stock Prices

End-of-period stock prices with calculated changes.

**Table: `stock_prices`**

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | Unique identifier |
| bank_id | TEXT | Bank identifier |
| fiscal_year | INTEGER | Fiscal year |
| fiscal_quarter | TEXT | Quarter (Q1, Q2, Q3, Q4) |
| close_price | DECIMAL | End of period closing price (CAD) |
| qoq_change_pct | DECIMAL | Quarter-over-quarter % change |
| yoy_change_pct | DECIMAL | Year-over-year % change |
| period_end_date | DATE | Last trading day of quarter |
| created_at | TIMESTAMP | Record creation time |

**Filters:**
- `bank_id`: Which bank
- `fiscal_year`: Which year
- `fiscal_quarter`: Which quarter

**Structure:** One row per bank per period.

---

## MCP Tools (Retrievers)

Each data source has a corresponding MCP tool that the agent calls.

### search_transcripts

```json
{
  "name": "search_transcripts",
  "description": "Retrieve earnings call transcript sections for Canadian banks (Big 6). Returns full section text.",
  "parameters": {
    "bank_id": {
      "type": "string",
      "enum": ["RY", "TD", "BMO", "BNS", "CM", "NA"],
      "description": "Bank identifier. RY=Royal Bank, TD=Toronto-Dominion, BMO=Bank of Montreal, BNS=Scotiabank, CM=CIBC, NA=National Bank"
    },
    "fiscal_year": {
      "type": "integer",
      "description": "Fiscal year (e.g., 2025)"
    },
    "fiscal_quarter": {
      "type": "string",
      "enum": ["Q1", "Q2", "Q3", "Q4"],
      "description": "Fiscal quarter"
    },
    "section": {
      "type": "string",
      "enum": ["management_discussion", "qa"],
      "description": "management_discussion = executive prepared remarks, qa = analyst Q&A"
    }
  }
}
```

### search_financials

```json
{
  "name": "search_financials",
  "description": "Get financial metrics for Canadian banks (Big 6). Returns metric values for specified bank/period.",
  "parameters": {
    "bank_id": {
      "type": "string",
      "enum": ["RY", "TD", "BMO", "BNS", "CM", "NA"],
      "description": "Bank identifier"
    },
    "fiscal_year": {
      "type": "integer",
      "description": "Fiscal year"
    },
    "fiscal_quarter": {
      "type": "string",
      "enum": ["Q1", "Q2", "Q3", "Q4"],
      "description": "Fiscal quarter"
    },
    "metric_id": {
      "type": "string",
      "description": "Optional: specific metric to retrieve. If omitted, returns all metrics."
    }
  }
}
```

### search_stock_prices

```json
{
  "name": "search_stock_prices",
  "description": "Get stock price data for Canadian banks (Big 6). Returns end-of-period price and changes.",
  "parameters": {
    "bank_id": {
      "type": "string",
      "enum": ["RY", "TD", "BMO", "BNS", "CM", "NA"],
      "description": "Bank identifier"
    },
    "fiscal_year": {
      "type": "integer",
      "description": "Fiscal year"
    },
    "fiscal_quarter": {
      "type": "string",
      "enum": ["Q1", "Q2", "Q3", "Q4"],
      "description": "Fiscal quarter"
    }
  }
}
```

---

## Agent Workflow

```
┌─────────────────────┐
│   User Question     │
│ "What did TD say    │
│  about credit?"     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Agent sees MCP     │  Tool definitions tell agent
│  tool definitions   │  what parameters are needed
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Agent calls tool   │  search_transcripts(
│                     │    bank_id="TD",
│                     │    fiscal_year=2025,
│                     │    fiscal_quarter="Q1",
│                     │    section="management_discussion"
│                     │  )
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Retriever executes │  Builds SQL, runs query,
│                     │  returns full section text
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Agent generates    │
│  response           │
└─────────────────────┘
```

---

## Project Structure

```
report-designer/
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md          # This file
│   ├── TODO.md                  # Project roadmap
│   └── DATA_SOURCES.md          # Real data source links (for future)
│
├── schemas/                     # PostgreSQL table definitions
│   ├── transcripts.sql
│   ├── financials.sql
│   └── stock_prices.sql
│
├── scripts/                     # Utility scripts
│   └── database/                # Database setup scripts
│       ├── generate_mock_data.py   # Generate mock JSON data
│       ├── load_data.py            # Load JSON into Postgres
│       ├── metrics.py              # 25 metric definitions
│       ├── database.py             # DB connection config
│       └── data/                   # Generated mock data
│           ├── transcripts.json
│           ├── financials.json
│           └── stock_prices.json
│
├── src/                         # Application code (future)
│   ├── retrievers/              # MCP tools
│   └── mcp_server.py            # MCP server
│
└── requirements.txt
```

---

## Tech Stack

- **Database:** PostgreSQL (port 34532)
- **MCP:** Model Context Protocol for tool exposure
- **Language:** Python

---

## Data Time Range

- **Periods:** FY2024 Q1-Q4, FY2025 Q1 (5 quarters)
- **Mock Data:** Semi-realistic data generated for development
- **Real Data:** Can be swapped in later via data pipelines
