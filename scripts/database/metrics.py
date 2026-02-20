"""
Financial Metrics Configuration

Defines the 25 standard metrics tracked across all Big 6 Canadian banks.
These metrics are commonly reported in quarterly supplementary financial packages.
"""

METRICS = [
    # Profitability (5)
    {
        "id": "total_revenue",
        "name": "Total Revenue",
        "unit": "CAD_millions",
        "category": "profitability",
        "description": "Total revenue including net interest income and non-interest revenue"
    },
    {
        "id": "net_income",
        "name": "Net Income",
        "unit": "CAD_millions",
        "category": "profitability",
        "description": "Net income attributable to shareholders"
    },
    {
        "id": "diluted_eps",
        "name": "Diluted EPS",
        "unit": "CAD",
        "category": "profitability",
        "description": "Diluted earnings per share"
    },
    {
        "id": "roe",
        "name": "Return on Equity",
        "unit": "percent",
        "category": "profitability",
        "description": "Return on common shareholders' equity"
    },
    {
        "id": "roa",
        "name": "Return on Assets",
        "unit": "percent",
        "category": "profitability",
        "description": "Return on average assets"
    },

    # Capital (4)
    {
        "id": "cet1_ratio",
        "name": "CET1 Ratio",
        "unit": "percent",
        "category": "capital",
        "description": "Common Equity Tier 1 capital ratio"
    },
    {
        "id": "tier1_ratio",
        "name": "Tier 1 Capital Ratio",
        "unit": "percent",
        "category": "capital",
        "description": "Tier 1 capital ratio"
    },
    {
        "id": "total_capital_ratio",
        "name": "Total Capital Ratio",
        "unit": "percent",
        "category": "capital",
        "description": "Total capital ratio"
    },
    {
        "id": "book_value_per_share",
        "name": "Book Value per Share",
        "unit": "CAD",
        "category": "capital",
        "description": "Book value per common share"
    },

    # Margins & Efficiency (4)
    {
        "id": "nim",
        "name": "Net Interest Margin",
        "unit": "percent",
        "category": "efficiency",
        "description": "Net interest margin on average earning assets"
    },
    {
        "id": "efficiency_ratio",
        "name": "Efficiency Ratio",
        "unit": "percent",
        "category": "efficiency",
        "description": "Non-interest expenses as percentage of revenue (lower is better)"
    },
    {
        "id": "operating_leverage",
        "name": "Operating Leverage",
        "unit": "percent",
        "category": "efficiency",
        "description": "Revenue growth minus expense growth"
    },
    {
        "id": "net_interest_income",
        "name": "Net Interest Income",
        "unit": "CAD_millions",
        "category": "efficiency",
        "description": "Interest income minus interest expense"
    },

    # Credit Quality (4)
    {
        "id": "pcl",
        "name": "Provision for Credit Losses",
        "unit": "CAD_millions",
        "category": "credit",
        "description": "Provision for credit losses"
    },
    {
        "id": "pcl_ratio",
        "name": "PCL Ratio",
        "unit": "bps",
        "category": "credit",
        "description": "PCL as basis points of average loans"
    },
    {
        "id": "gross_impaired_loans",
        "name": "Gross Impaired Loans",
        "unit": "CAD_millions",
        "category": "credit",
        "description": "Total gross impaired loans"
    },
    {
        "id": "gil_ratio",
        "name": "Gross Impaired Loan Ratio",
        "unit": "percent",
        "category": "credit",
        "description": "Gross impaired loans as percentage of total loans"
    },

    # Balance Sheet (5)
    {
        "id": "total_assets",
        "name": "Total Assets",
        "unit": "CAD_billions",
        "category": "balance_sheet",
        "description": "Total assets"
    },
    {
        "id": "total_loans",
        "name": "Total Loans",
        "unit": "CAD_billions",
        "category": "balance_sheet",
        "description": "Total loans and acceptances"
    },
    {
        "id": "total_deposits",
        "name": "Total Deposits",
        "unit": "CAD_billions",
        "category": "balance_sheet",
        "description": "Total deposits"
    },
    {
        "id": "loan_to_deposit_ratio",
        "name": "Loan-to-Deposit Ratio",
        "unit": "percent",
        "category": "balance_sheet",
        "description": "Total loans divided by total deposits"
    },
    {
        "id": "common_equity",
        "name": "Common Equity",
        "unit": "CAD_billions",
        "category": "balance_sheet",
        "description": "Common shareholders' equity"
    },

    # Other (3)
    {
        "id": "non_interest_revenue",
        "name": "Non-Interest Revenue",
        "unit": "CAD_millions",
        "category": "other",
        "description": "Fee income, trading, wealth management, and other non-interest revenue"
    },
    {
        "id": "aum",
        "name": "Assets Under Management",
        "unit": "CAD_billions",
        "category": "other",
        "description": "Total assets under management in wealth businesses"
    },
    {
        "id": "dividend_per_share",
        "name": "Dividend per Share",
        "unit": "CAD",
        "category": "other",
        "description": "Quarterly dividend per common share"
    },
]

# Bank profiles for generating realistic mock data
BANK_PROFILES = {
    "RY": {
        "name": "Royal Bank of Canada",
        "size": "largest",
        "strengths": ["wealth_management", "capital_markets"],
        "themes": ["strong earnings", "wealth growth", "digital transformation"]
    },
    "TD": {
        "name": "Toronto-Dominion Bank",
        "size": "large",
        "strengths": ["us_retail", "deposits"],
        "themes": ["US operations", "regulatory remediation", "deposit franchise"]
    },
    "BMO": {
        "name": "Bank of Montreal",
        "size": "large",
        "strengths": ["us_midwest", "commercial"],
        "themes": ["Bank of the West integration", "US growth", "operating leverage"]
    },
    "BNS": {
        "name": "Bank of Nova Scotia",
        "size": "large",
        "strengths": ["international", "latam"],
        "themes": ["restructuring", "refocusing on core markets", "credit normalization"]
    },
    "CM": {
        "name": "Canadian Imperial Bank of Commerce",
        "size": "medium",
        "strengths": ["canadian_retail", "mortgages"],
        "themes": ["Canadian focus", "mortgage growth", "capital strength"]
    },
    "NA": {
        "name": "National Bank of Canada",
        "size": "smallest",
        "strengths": ["quebec", "growth"],
        "themes": ["outperformance", "Quebec strength", "expansion outside Quebec"]
    }
}
