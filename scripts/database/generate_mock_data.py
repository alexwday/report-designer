"""
Mock Data Generator

Generates semi-realistic mock data for all Big 6 Canadian banks
across multiple quarters for testing the retrieval system.

Usage: python scripts/database/generate_mock_data.py
"""

import json
import random
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"

# Periods to generate (Canadian bank fiscal year ends Oct 31)
# Q1 = Nov-Jan, Q2 = Feb-Apr, Q3 = May-Jul, Q4 = Aug-Oct
PERIODS = [
    {"fiscal_year": 2024, "fiscal_quarter": "Q1", "call_date": "2024-02-28", "period_end": "2024-01-31"},
    {"fiscal_year": 2024, "fiscal_quarter": "Q2", "call_date": "2024-05-23", "period_end": "2024-04-30"},
    {"fiscal_year": 2024, "fiscal_quarter": "Q3", "call_date": "2024-08-28", "period_end": "2024-07-31"},
    {"fiscal_year": 2024, "fiscal_quarter": "Q4", "call_date": "2024-12-04", "period_end": "2024-10-31"},
    {"fiscal_year": 2025, "fiscal_quarter": "Q1", "call_date": "2025-02-27", "period_end": "2025-01-31"},
]

# Bank configurations with base metrics and themes
BANKS = {
    "RY": {
        "name": "Royal Bank of Canada",
        "ceo": "Dave McKay",
        "cfo": "Katherine Gibson",
        "cro": "Graeme Hepworth",
        "themes": ["wealth management leadership", "digital transformation", "capital markets strength"],
        "base_metrics": {
            "total_revenue": 14500, "net_income": 4200, "diluted_eps": 2.95,
            "roe": 15.5, "roa": 0.95, "cet1_ratio": 12.8, "tier1_ratio": 14.3,
            "total_capital_ratio": 16.0, "book_value_per_share": 85.0, "nim": 2.62,
            "efficiency_ratio": 52.5, "operating_leverage": 2.0, "net_interest_income": 8200,
            "pcl": 850, "pcl_ratio": 24, "gross_impaired_loans": 4200, "gil_ratio": 0.48,
            "total_assets": 2050, "total_loans": 880, "total_deposits": 1120,
            "loan_to_deposit_ratio": 78.6, "common_equity": 120, "non_interest_revenue": 6300,
            "aum": 1320, "dividend_per_share": 1.35
        },
        "stock_base": 155.0
    },
    "TD": {
        "name": "Toronto-Dominion Bank",
        "ceo": "Bharat Masrani",
        "cfo": "Kelvin Tran",
        "cro": "Ajai Bambawale",
        "themes": ["US retail banking", "regulatory remediation", "deposit franchise strength"],
        "base_metrics": {
            "total_revenue": 13500, "net_income": 3200, "diluted_eps": 1.78,
            "roe": 11.5, "roa": 0.72, "cet1_ratio": 12.5, "tier1_ratio": 14.0,
            "total_capital_ratio": 16.2, "book_value_per_share": 62.0, "nim": 2.78,
            "efficiency_ratio": 56.0, "operating_leverage": 0.5, "net_interest_income": 8500,
            "pcl": 1200, "pcl_ratio": 52, "gross_impaired_loans": 5200, "gil_ratio": 0.55,
            "total_assets": 1900, "total_loans": 920, "total_deposits": 1200,
            "loan_to_deposit_ratio": 76.7, "common_equity": 108, "non_interest_revenue": 5000,
            "aum": 510, "dividend_per_share": 1.00
        },
        "stock_base": 82.0
    },
    "BMO": {
        "name": "Bank of Montreal",
        "ceo": "Darryl White",
        "cfo": "Tayfun Tuzun",
        "cro": "Piyush Agrawal",
        "themes": ["Bank of the West integration", "US expansion", "operating leverage"],
        "base_metrics": {
            "total_revenue": 7800, "net_income": 1950, "diluted_eps": 2.62,
            "roe": 10.5, "roa": 0.75, "cet1_ratio": 13.0, "tier1_ratio": 14.6,
            "total_capital_ratio": 16.5, "book_value_per_share": 102.0, "nim": 2.65,
            "efficiency_ratio": 58.0, "operating_leverage": 5.0, "net_interest_income": 4800,
            "pcl": 580, "pcl_ratio": 52, "gross_impaired_loans": 3100, "gil_ratio": 0.68,
            "total_assets": 1100, "total_loans": 450, "total_deposits": 680,
            "loan_to_deposit_ratio": 66.2, "common_equity": 74, "non_interest_revenue": 3000,
            "aum": 360, "dividend_per_share": 1.51
        },
        "stock_base": 118.0
    },
    "BNS": {
        "name": "Bank of Nova Scotia",
        "ceo": "Scott Thomson",
        "cfo": "Raj Viswanathan",
        "cro": "Phil Thomas",
        "themes": ["international restructuring", "Latin America exposure", "refocusing on core markets"],
        "base_metrics": {
            "total_revenue": 8200, "net_income": 1850, "diluted_eps": 1.42,
            "roe": 9.5, "roa": 0.62, "cet1_ratio": 12.5, "tier1_ratio": 14.0,
            "total_capital_ratio": 15.8, "book_value_per_share": 60.0, "nim": 2.40,
            "efficiency_ratio": 59.5, "operating_leverage": -1.5, "net_interest_income": 4800,
            "pcl": 980, "pcl_ratio": 52, "gross_impaired_loans": 5800, "gil_ratio": 0.75,
            "total_assets": 1280, "total_loans": 775, "total_deposits": 860,
            "loan_to_deposit_ratio": 90.1, "common_equity": 78, "non_interest_revenue": 3400,
            "aum": 320, "dividend_per_share": 1.03
        },
        "stock_base": 65.0
    },
    "CM": {
        "name": "Canadian Imperial Bank of Commerce",
        "ceo": "Victor Dodig",
        "cfo": "Hratch Panossian",
        "cro": "Shawn Beber",
        "themes": ["Canadian focus", "mortgage strength", "capital efficiency"],
        "base_metrics": {
            "total_revenue": 6200, "net_income": 1650, "diluted_eps": 1.72,
            "roe": 12.5, "roa": 0.82, "cet1_ratio": 13.0, "tier1_ratio": 14.5,
            "total_capital_ratio": 16.0, "book_value_per_share": 56.0, "nim": 2.70,
            "efficiency_ratio": 54.5, "operating_leverage": 1.5, "net_interest_income": 3700,
            "pcl": 420, "pcl_ratio": 32, "gross_impaired_loans": 2000, "gil_ratio": 0.40,
            "total_assets": 880, "total_loans": 510, "total_deposits": 650,
            "loan_to_deposit_ratio": 78.5, "common_equity": 54, "non_interest_revenue": 2500,
            "aum": 300, "dividend_per_share": 0.87
        },
        "stock_base": 72.0
    },
    "NA": {
        "name": "National Bank of Canada",
        "ceo": "Laurent Ferreira",
        "cfo": "Marie Chantal Gingras",
        "cro": "William Bonnell",
        "themes": ["Quebec leadership", "consistent outperformance", "expansion outside Quebec"],
        "base_metrics": {
            "total_revenue": 2650, "net_income": 880, "diluted_eps": 2.48,
            "roe": 17.0, "roa": 1.00, "cet1_ratio": 13.2, "tier1_ratio": 14.8,
            "total_capital_ratio": 16.5, "book_value_per_share": 60.0, "nim": 2.85,
            "efficiency_ratio": 53.0, "operating_leverage": 3.5, "net_interest_income": 1580,
            "pcl": 125, "pcl_ratio": 21, "gross_impaired_loans": 620, "gil_ratio": 0.26,
            "total_assets": 400, "total_loans": 235, "total_deposits": 280,
            "loan_to_deposit_ratio": 83.9, "common_equity": 21, "non_interest_revenue": 1070,
            "aum": 140, "dividend_per_share": 1.06
        },
        "stock_base": 108.0
    }
}

# Transcript templates
MD_TEMPLATES = {
    "RY": """Good morning everyone. I'm {ceo}, President and CEO of Royal Bank of Canada. We're pleased to report {quarter_desc} results that demonstrate the strength of our diversified business model.

Net income for the quarter was {net_income}, {income_change} from last year, with diluted EPS of {eps}. {performance_note}

Our Canadian Banking segment delivered {canadian_banking_performance} with {canadian_detail}. We continue to see solid demand across our product lines and our digital adoption rates continue to climb.

Wealth Management had {wealth_performance} with assets under administration reaching {aum}. Our high-net-worth business continues to gain share as clients value our comprehensive advisory capabilities and global platform.

Capital Markets {capital_markets_performance}. Our global markets franchise {cm_detail} and we continue to build our sustainable finance capabilities.

Credit quality {credit_quality_note} with PCL ratio of {pcl_ratio}. {credit_detail}

Our CET1 ratio of {cet1}% provides substantial flexibility for growth and capital return. {capital_note}

Looking ahead, {outlook}

I'll now turn it over to {cfo}, our CFO, to provide more details on our financial performance.""",

    "TD": """Good morning and thank you for joining us. I'm {ceo}, Group President and CEO of TD Bank Group.

We reported {quarter_desc} earnings of {net_income} on an adjusted basis, {performance_note}. Diluted EPS was {eps} on an adjusted basis.

{remediation_update}

Our Canadian Personal and Commercial Bank delivered {canadian_banking_performance}. We continue to benefit from our leading deposit franchise, with market share above 22%. {canadian_detail}

In US Retail, {us_retail_performance}. {us_detail}

Wealth Management and Insurance {wealth_performance}. Our direct investing platform continues to gain clients and we're seeing strong engagement with our digital tools.

Wholesale Banking {wholesale_performance}. Our corporate lending book remains well-positioned with a focus on investment-grade clients.

Our CET1 ratio {cet1_note} this quarter. {capital_note}

Credit quality {credit_quality_note} with PCL of {pcl_ratio}. {credit_detail}

Looking ahead, {outlook}

I'll now turn the call over to {cfo}, our CFO.""",

    "BMO": """Good morning everyone. I'm {ceo}, CEO of BMO Financial Group.

We delivered {quarter_desc} with adjusted net income of {net_income} and EPS of {eps}. {performance_note}

{integration_update}

Canadian Personal and Commercial Banking delivered {canadian_banking_performance}. {canadian_detail}

US Personal and Commercial Banking {us_performance}. {us_detail}

BMO Capital Markets had {capital_markets_performance}. Our North American platform is winning share with corporate clients and we're building our presence in sustainable finance.

BMO Wealth Management {wealth_performance}. Our private banking business continues to attract high-net-worth clients in both Canada and the US.

Credit quality {credit_quality_note} with PCL of {pcl_ratio}. {credit_detail}

Our CET1 ratio of {cet1}% {capital_note}. Operating leverage was {op_leverage}% this quarter.

Looking ahead, {outlook}

I'll now turn it over to {cfo}, our CFO.""",

    "BNS": """Good morning and thank you for joining us. I'm {ceo}, President and CEO of Scotiabank.

We reported {quarter_desc} net income of {net_income} with diluted EPS of {eps}. {performance_note}

{strategy_update}

Canadian Banking delivered {canadian_banking_performance}. {canadian_detail}

International Banking {international_performance}. {international_detail}

Global Wealth Management {wealth_performance}. Our Canadian wealth business is gaining share and our digital investing platforms are seeing strong engagement.

Global Banking and Markets {gbm_performance}. Our focus on deepening client relationships is paying off.

Credit quality {credit_quality_note} with PCL of {pcl_ratio}. {credit_detail}

Our CET1 ratio of {cet1}% {capital_note}.

{outlook}

I'll now turn it over to {cfo}, our CFO.""",

    "CM": """Good morning everyone. I'm {ceo}, President and CEO of CIBC.

We delivered {quarter_desc} results with net income of {net_income} and diluted EPS of {eps}. {performance_note}

{strategic_note}

Canadian Personal and Business Banking {canadian_banking_performance}. {canadian_detail}

Canadian Commercial Banking and Wealth Management {commercial_wealth_performance}. {commercial_detail}

US Commercial Banking and Wealth Management {us_performance}. {us_detail}

Capital Markets {capital_markets_performance}. Our client-focused approach continues to differentiate us in Canadian capital markets.

Credit quality {credit_quality_note} with PCL of {pcl_ratio}. {credit_detail}

Our CET1 ratio of {cet1}% {capital_note}. We continue to invest in technology and our digital capabilities.

Looking ahead, {outlook}

I'll now turn it over to {cfo}, our CFO.""",

    "NA": """Good morning everyone. I'm {ceo}, President and CEO of National Bank of Canada.

We delivered {quarter_desc} with net income of {net_income}, {income_change} from last year, and diluted EPS of {eps}. {performance_note}

National Bank has consistently delivered superior returns among Canadian banks. Our ROE of {roe}% this quarter remains industry-leading.

Personal and Commercial Banking in Quebec delivered {quebec_performance}. {quebec_detail}

Wealth Management had {wealth_performance}. {wealth_detail}

Financial Markets delivered {fm_performance}. {fm_detail}

US Specialty Finance and International {usfi_performance}.

{expansion_note}

Credit quality {credit_quality_note} with PCL of {pcl_ratio}. {credit_detail}

Our CET1 ratio of {cet1}% {capital_note}.

{outlook}

I'll now turn it over to {cfo}, our CFO."""
}

QA_TEMPLATES = {
    "RY": """Operator: We'll now begin the question and answer session. Our first question comes from {analyst1} with {firm1}.

{analyst1}: Good morning. {ceo}, can you talk about {question1}?

{ceo}: {answer1}

{analyst1}: And on {followup1}?

{cro}: {followup_answer1}

Operator: Our next question comes from {analyst2} with {firm2}.

{analyst2}: Good morning. {question2}?

{ceo}: {answer2}

{analyst2}: And on expenses, {expense_question}?

{cfo}: {expense_answer}

Operator: Our next question comes from {analyst3} with {firm3}.

{analyst3}: {question3}?

{ceo}: {answer3}

Operator: That concludes our Q&A session. Thank you for participating in today's call.""",

    "TD": """Operator: We'll now begin the question and answer session. Our first question comes from {analyst1} with {firm1}.

{analyst1}: Good morning. {ceo}, {question1}?

{ceo}: {answer1}

{analyst1}: And {followup1}?

{ceo}: {followup_answer1}

Operator: Our next question comes from {analyst2} with {firm2}.

{analyst2}: Good morning. {question2}?

{cfo}: {answer2}

{analyst2}: And on {followup2}?

{cfo}: {followup_answer2}

Operator: Our next question comes from {analyst3} with {firm3}.

{analyst3}: {question3}?

{ceo}: {answer3}

Operator: That concludes our Q&A session. Thank you for participating.""",

    "BMO": """Operator: We'll now begin the question and answer session. Our first question comes from {analyst1} with {firm1}.

{analyst1}: Good morning. {ceo}, {question1}?

{ceo}: {answer1}

{analyst1}: And {followup1}?

{ceo}: {followup_answer1}

Operator: Our next question comes from {analyst2} with {firm2}.

{analyst2}: Good morning. {question2}?

{cro}: {answer2}

{analyst2}: And on capital, {capital_question}?

{cfo}: {capital_answer}

Operator: Our next question comes from {analyst3} with {firm3}.

{analyst3}: {ceo}, {question3}?

{ceo}: {answer3}

Operator: That concludes our Q&A session. Thank you for joining us today.""",

    "BNS": """Operator: We'll now begin the question and answer session. Our first question comes from {analyst1} with {firm1}.

{analyst1}: Good morning {ceo}. {question1}?

{ceo}: {answer1}

{analyst1}: And {followup1}?

{ceo}: {followup_answer1}

Operator: Our next question comes from {analyst2} with {firm2}.

{analyst2}: Good morning. {question2}?

{cro}: {answer2}

{analyst2}: And on {followup2}?

{cro}: {followup_answer2}

Operator: Our next question comes from {analyst3} with {firm3}.

{analyst3}: {ceo}, {question3}?

{ceo}: {answer3}

Operator: That concludes our Q&A session. Thank you for participating.""",

    "CM": """Operator: We'll now begin the question and answer session. Our first question comes from {analyst1} with {firm1}.

{analyst1}: Good morning {ceo}. {question1}?

{ceo}: {answer1}

{analyst1}: And on {followup1}?

{ceo}: {followup_answer1}

Operator: Our next question comes from {analyst2} with {firm2}.

{analyst2}: Good morning. {question2}?

{ceo}: {answer2}

{analyst2}: And on expenses, {expense_question}?

{cfo}: {expense_answer}

Operator: Our next question comes from {analyst3} with {firm3}.

{analyst3}: {ceo}, {question3}?

{ceo}: {answer3}

Operator: That concludes our Q&A session. Thank you for joining us today.""",

    "NA": """Operator: We'll now begin the question and answer session. Our first question comes from {analyst1} with {firm1}.

{analyst1}: Good morning {ceo}. {question1}?

{ceo}: {answer1}

{analyst1}: {followup1}?

{ceo}: {followup_answer1}

Operator: Our next question comes from {analyst2} with {firm2}.

{analyst2}: Good morning. {question2}?

{ceo}: {answer2}

{analyst2}: And {followup2}?

{ceo}: {followup_answer2}

Operator: Our next question comes from {analyst3} with {firm3}.

{analyst3}: {ceo}, {question3}?

{ceo}: {answer3}

Operator: That concludes our Q&A session. Thank you for participating in today's call."""
}

# Analysts for Q&A
ANALYSTS = [
    ("Gabriel Dechaine", "National Bank Financial"),
    ("Ebrahim Poonawala", "Bank of America"),
    ("Meny Grauman", "Scotiabank"),
    ("Doug Young", "Desjardins"),
    ("Darko Mihelic", "RBC Capital Markets"),
    ("Scott Chan", "Canaccord Genuity"),
    ("Paul Holden", "CIBC"),
    ("John Aiken", "Barclays"),
    ("Nigel D'Souza", "Veritas Investment Research"),
    ("Sohrab Movahedi", "BMO Capital Markets"),
    ("Lemar Persaud", "Cormark Securities"),
    ("Mario Mendonca", "TD Securities"),
]


def format_currency(value, unit):
    """Format currency values for display."""
    if unit == "CAD_millions":
        if value >= 1000:
            return f"${value/1000:.1f}B"
        return f"${value:.0f}M"
    elif unit == "CAD_billions":
        return f"${value:.0f}B"
    elif unit == "CAD":
        return f"${value:.2f}"
    elif unit == "percent":
        return f"{value:.1f}%"
    elif unit == "bps":
        return f"{value:.0f} bps"
    return str(value)


def get_quarter_variation(quarter_idx):
    """Get growth multiplier based on quarter progression."""
    # Simulate gradual growth over quarters
    base_growth = 1 + (quarter_idx * 0.02)  # ~2% per quarter
    seasonal = [0.98, 1.0, 0.99, 1.03, 1.02][quarter_idx]  # Q4 typically strong
    return base_growth * seasonal


def generate_metrics(bank_id, period_idx):
    """Generate financial metrics for a bank/period."""
    bank = BANKS[bank_id]
    base = bank["base_metrics"]
    variation = get_quarter_variation(period_idx)

    metrics = {}
    for metric_id, base_value in base.items():
        # Add some randomness
        random_factor = random.uniform(0.97, 1.03)
        value = base_value * variation * random_factor

        # Determine unit based on metric
        if metric_id in ["total_revenue", "net_income", "net_interest_income", "pcl",
                         "gross_impaired_loans", "non_interest_revenue"]:
            unit = "CAD_millions"
        elif metric_id in ["total_assets", "total_loans", "total_deposits", "common_equity", "aum"]:
            unit = "CAD_billions"
        elif metric_id in ["diluted_eps", "book_value_per_share", "dividend_per_share"]:
            unit = "CAD"
        elif metric_id == "pcl_ratio":
            unit = "bps"
        else:
            unit = "percent"

        # Round appropriately
        if unit == "CAD":
            value = round(value, 2)
        elif unit in ["percent", "bps"]:
            value = round(value, 1)
        else:
            value = round(value, 0)

        metrics[metric_id] = {
            "value": value,
            "formatted": format_currency(value, unit)
        }

    return metrics


def generate_stock_price(bank_id, period_idx):
    """Generate stock price data for a bank/period."""
    bank = BANKS[bank_id]
    base_price = bank["stock_base"]

    # Calculate price based on quarter progression
    growth_rate = 0.03  # ~3% per quarter average
    price = base_price * (1 + growth_rate) ** period_idx

    # Add randomness
    price *= random.uniform(0.95, 1.05)
    price = round(price, 2)

    # Calculate changes
    if period_idx > 0:
        prev_price = base_price * (1 + growth_rate) ** (period_idx - 1)
        qoq = round((price / prev_price - 1) * 100, 1)
    else:
        qoq = round(random.uniform(-2, 5), 1)

    if period_idx >= 4:
        yoy_prev = base_price * (1 + growth_rate) ** (period_idx - 4)
        yoy = round((price / yoy_prev - 1) * 100, 1)
    else:
        yoy = round(random.uniform(-5, 15), 1)

    return {
        "close_price": price,
        "qoq_change_pct": qoq,
        "yoy_change_pct": yoy
    }


def generate_transcript_content(bank_id, period, metrics):
    """Generate transcript content for a bank/period."""
    bank = BANKS[bank_id]
    period_idx = PERIODS.index(period)
    quarter = period["fiscal_quarter"]
    year = period["fiscal_year"]

    # Quarter descriptions
    quarter_descs = {
        "Q1": "first quarter",
        "Q2": "second quarter",
        "Q3": "third quarter",
        "Q4": "fourth quarter and full year"
    }

    # Performance descriptors based on metrics
    net_income = metrics["net_income"]["value"]
    prev_income = net_income / (1 + random.uniform(0.02, 0.08))
    income_change = "up" if net_income > prev_income else "down"
    pct_change = abs((net_income / prev_income - 1) * 100)

    # Build context for templates
    context = {
        "ceo": bank["ceo"],
        "cfo": bank["cfo"],
        "cro": bank["cro"],
        "quarter_desc": quarter_descs[quarter],
        "net_income": metrics["net_income"]["formatted"],
        "eps": metrics["diluted_eps"]["formatted"],
        "cet1": metrics["cet1_ratio"]["value"],
        "pcl_ratio": metrics["pcl_ratio"]["formatted"],
        "aum": metrics["aum"]["formatted"],
        "roe": metrics["roe"]["value"],
        "op_leverage": metrics["operating_leverage"]["value"],
        "income_change": f"{income_change} {pct_change:.0f}%",
    }

    # Bank-specific content
    if bank_id == "RY":
        context.update({
            "performance_note": "This reflects the strength of our diversified business model." if period_idx > 2 else "We're building momentum across our businesses.",
            "canadian_banking_performance": "solid results with revenue growth of 6%" if quarter != "Q4" else "strong results with revenue growth of 8%",
            "canadian_detail": "We continue to see good demand for mortgages and our digital adoption rates exceeded 85%.",
            "wealth_performance": "an excellent quarter with earnings up 15%" if period_idx > 2 else "a good quarter with steady growth",
            "capital_markets_performance": "delivered exceptional results with revenues up 25%" if quarter in ["Q1", "Q4"] else "performed well despite market volatility",
            "cm_detail": "benefited from increased client activity and favorable market conditions",
            "credit_quality_note": "remains strong" if metrics["pcl_ratio"]["value"] < 30 else "normalized as expected",
            "credit_detail": "We continue to maintain robust allowances and our diversified portfolio limits concentration risk.",
            "capital_note": "We're well positioned for growth and capital return.",
            "outlook": "we're confident in our trajectory and well positioned to navigate the evolving economic environment."
        })
    elif bank_id == "TD":
        context.update({
            "performance_note": "demonstrating the resilience of our franchise.",
            "remediation_update": "We continue to make progress strengthening our risk and control environment in our US operations. We've enhanced our AML compliance program and added experienced leadership." if period_idx < 4 else "We've made substantial progress on our US remediation efforts and are seeing the results of our investments.",
            "canadian_banking_performance": "solid results with revenue growth of 4%",
            "canadian_detail": "Net interest margin was stable as the benefits of higher rates offset competitive pressures.",
            "us_retail_performance": "we saw revenue growth of 2% on a constant currency basis" if period_idx < 3 else "showed improving trends with revenue growth of 4%",
            "us_detail": "Our deposit franchise remained strong with market share stable.",
            "wealth_performance": "had a good quarter with AUM reaching $520 billion",
            "wholesale_performance": "delivered improved results with trading revenues up",
            "cet1_note": "increased to " + str(metrics["cet1_ratio"]["value"]) + "%",
            "capital_note": "This provides flexibility for growth once we complete our remediation work.",
            "credit_quality_note": "remained stable" if metrics["pcl_ratio"]["value"] < 55 else "reflected normalization",
            "credit_detail": "We're maintaining prudent reserves given economic uncertainty.",
            "outlook": "our priority remains executing on our strategic initiatives and strengthening our US franchise."
        })
    elif bank_id == "BMO":
        context.update({
            "performance_note": "These results demonstrate the earnings power of our diversified North American franchise.",
            "integration_update": "We continue to make progress on the Bank of the West integration with synergies tracking ahead of plan." if period_idx < 4 else "The Bank of the West integration is largely complete and we're now operating as one bank across our US footprint.",
            "canadian_banking_performance": "revenue growth of 5% with solid loan growth",
            "canadian_detail": "Our market share in business banking remained strong.",
            "us_performance": "saw continued momentum with revenue growth of 12%",
            "us_detail": "Client retention has exceeded expectations and we're winning new relationships.",
            "capital_markets_performance": "an excellent quarter with revenue up 20%",
            "wealth_performance": "grew earnings by 12% with assets under management reaching record levels",
            "credit_quality_note": "remained stable" if metrics["pcl_ratio"]["value"] < 55 else "normalized as expected",
            "credit_detail": "We're maintaining strong allowances and our diversified portfolio limits concentration risk.",
            "capital_note": "is at the top of our target range, providing flexibility for organic growth",
            "outlook": "we're focused on realizing the full potential of our North American franchise."
        })
    elif bank_id == "BNS":
        context.update({
            "performance_note": "While these results reflect ongoing headwinds in some international markets, we're making progress on our strategic repositioning." if period_idx < 3 else "These results show the early benefits of our strategic refocusing.",
            "strategy_update": "We continue to execute on our strategy of focusing resources on our core markets of Canada, Mexico, and select international operations.",
            "canadian_banking_performance": "solid results with revenue growth of 3%",
            "canadian_detail": "We continue to invest in digital capabilities.",
            "international_performance": "showed resilience despite challenging conditions" if period_idx < 3 else "showed improvement with Mexico contributing strongly",
            "international_detail": "Mexico remains our priority international market with significant opportunity.",
            "wealth_performance": "had a good quarter with AUM growth",
            "gbm_performance": "delivered improved results",
            "credit_quality_note": "normalized" if metrics["pcl_ratio"]["value"] > 50 else "improved",
            "credit_detail": "Latin American provisions remain elevated but in line with expectations.",
            "capital_note": "provides adequate flexibility",
            "outlook": "I'm confident we're building a more focused and profitable bank."
        })
    elif bank_id == "CM":
        context.update({
            "performance_note": "Our focused strategy on being a relationship-oriented bank continues to drive growth.",
            "strategic_note": "CIBC's Canadian focus remains a source of strength.",
            "canadian_banking_performance": "grew revenue by 4% with balanced growth across products",
            "canadian_detail": "Our mortgage portfolio grew 3%, maintaining our strong market position.",
            "commercial_wealth_performance": "had an excellent quarter",
            "commercial_detail": "Commercial loan growth of 6% reflected strong demand from mid-market clients.",
            "us_performance": "delivered stable results",
            "us_detail": "Our focused US franchise serving clients with Canadian connections continues to perform well.",
            "capital_markets_performance": "performed well with revenue up 15%",
            "credit_quality_note": "was solid" if metrics["pcl_ratio"]["value"] < 40 else "normalized as expected",
            "credit_detail": "Our conservative underwriting approach has resulted in a high-quality loan portfolio.",
            "capital_note": "is among the highest in our peer group, providing substantial flexibility",
            "outlook": "we're confident in our strategy and well positioned for continued success."
        })
    elif bank_id == "NA":
        context.update({
            "performance_note": "These results continue our track record of outperformance.",
            "quebec_performance": "excellent results with revenue growth of 6%",
            "quebec_detail": "Our market position in Quebec remains exceptionally strong.",
            "wealth_performance": "an outstanding quarter with earnings up 18%",
            "wealth_detail": "Our full-service brokerage platform continues to attract advisors and clients.",
            "fm_performance": "strong results with revenue up 20%",
            "fm_detail": "Our trading and fixed income businesses performed well.",
            "usfi_performance": "continues to grow profitably",
            "expansion_note": "Our expansion outside Quebec remains a strategic priority. We're building our commercial banking presence in key markets.",
            "credit_quality_note": "was excellent" if metrics["pcl_ratio"]["value"] < 25 else "remained strong",
            "credit_detail": "Our conservative Quebec-focused portfolio continues to deliver below-peer credit costs.",
            "capital_note": "provides substantial flexibility",
            "outlook": "I'm proud of what our team continues to achieve. Our focused strategy positions us well for continued outperformance."
        })

    # Generate MD section
    md_content = MD_TEMPLATES[bank_id].format(**context)

    # Generate QA section
    analysts = random.sample(ANALYSTS, 3)
    qa_context = {
        "ceo": bank["ceo"],
        "cfo": bank["cfo"],
        "cro": bank["cro"],
        "analyst1": analysts[0][0],
        "firm1": analysts[0][1],
        "analyst2": analysts[1][0],
        "firm2": analysts[1][1],
        "analyst3": analysts[2][0],
        "firm3": analysts[2][1],
    }

    # Bank-specific Q&A content
    if bank_id == "RY":
        qa_context.update({
            "question1": "the outlook for Canadian mortgage growth given the rate environment",
            "answer1": "We're seeing steady demand in the mortgage market. As rates potentially decline, we expect to see some pickup in activity. Our focus remains on quality originations.",
            "followup1": "credit in the consumer portfolio",
            "followup_answer1": "Overall credit performance remains solid. Delinquencies remain well within historical ranges.",
            "question2": "Can you discuss the sustainability of the capital markets performance",
            "answer2": "While we benefited from favorable conditions, our capital markets franchise has been consistently gaining share. We've invested in talent and technology.",
            "expense_question": "how should we think about the efficiency ratio",
            "expense_answer": "We delivered positive operating leverage this quarter. Our technology investments are driving automation savings.",
            "question3": "On wealth management, can you talk about the competitive environment",
            "answer3": "Talent is always competitive. We've been successful in recruiting through our industry-leading platform and training programs."
        })
    elif bank_id == "TD":
        qa_context.update({
            "question1": "can you provide an update on the timeline for completing the AML remediation",
            "answer1": "We're making substantial progress. We've added over 1,500 people focused on compliance and are upgrading systems. This is a multi-year journey and we're committed to getting it right.",
            "followup1": "how should we think about growth in US Retail once remediation is complete",
            "followup_answer1": "We remain committed to the US market. Once we're through this period, we'll look at opportunities to grow. Near-term focus is on execution.",
            "question2": "Can you talk about net interest margin outlook given potential rate cuts",
            "answer2": "We're well positioned for various rate scenarios. We've been extending duration on the securities portfolio. We expect NIM to remain relatively stable.",
            "followup2": "expenses - what's driving the increase",
            "followup_answer2": "Expense growth reflects our investments in risk and control infrastructure. We expect growth to moderate as we achieve efficiencies.",
            "question3": "Can you discuss the outlook for the Schwab stake",
            "answer3": "We plan to manage our position over time in an orderly manner. The timing will depend on market conditions."
        })
    elif bank_id == "BMO":
        qa_context.update({
            "question1": "now that integration is progressing, how should we think about growth opportunities in the US",
            "answer1": "We're excited about our US positioning. The focus near-term is on driving revenue synergies - cross-selling and bringing our full product suite to customers.",
            "followup1": "can you quantify the revenue synergy opportunity",
            "followup_answer1": "We're making good progress on our synergy targets. Mortgage referrals and treasury management cross-sell are up significantly.",
            "question2": "Can you talk about the commercial real estate portfolio",
            "answer2": "Our CRE portfolio is well-diversified. Office represents less than 10% and is primarily in Canada with strong tenants. We're comfortable with our reserves.",
            "capital_question": "with CET1 strong, is there room for additional buybacks",
            "capital_answer": "We have capacity for buybacks and evaluate it regularly. We want to maintain flexibility while also returning capital to shareholders.",
            "question3": "how are you thinking about the competitive environment in California",
            "answer3": "California is a dynamic market with strong demographics. We have advantages - our commercial expertise and now meaningful scale. Client feedback has been positive."
        })
    elif bank_id == "BNS":
        qa_context.update({
            "question1": "Can you provide more details on the timeline for exiting certain Latin American markets",
            "answer1": "We're making good progress on announced transactions. We expect to close the majority by mid-year with some extending into the second half.",
            "followup1": "how should we think about reinvesting that capital",
            "followup_answer1": "Our priority is strengthening the balance sheet and investing in core markets. Canada and Mexico offer attractive opportunities.",
            "question2": "Can you discuss credit trends in your Canadian retail portfolio",
            "answer2": "Canadian retail credit remains in good shape. Delinquencies have normalized but are within historical ranges.",
            "followup2": "Mexico credit outlook",
            "followup_answer2": "Mexico PCLs are running higher than Canada but in line with expectations. Our through-the-cycle provisioning means we're comfortable with reserves.",
            "question3": "your efficiency ratio remains above peers - what's the path to closing that gap",
            "answer3": "Improving efficiency is a key priority. The international rationalization will help. We're also investing in automation and digitization."
        })
    elif bank_id == "CM":
        qa_context.update({
            "question1": "Your mortgage book continues to outperform - what's driving that",
            "answer1": "A few factors. Conservative underwriting, concentration in urban markets with stronger fundamentals, and our portfolio mix skews toward lower LTV borrowers.",
            "followup1": "market share in a potentially busier refinancing market",
            "followup_answer1": "We're well positioned for increased activity. Our branch network and mobile origination tools are excellent.",
            "question2": "Can you discuss the outlook for capital markets",
            "answer2": "Our capital markets business is designed to be less volatile given our client focus. We're gaining share in advisory and our trading desk has invested in capabilities.",
            "expense_question": "how should we think about the trajectory",
            "expense_answer": "We're committed to positive operating leverage. We continue to invest in technology while achieving efficiencies in other areas.",
            "question3": "do you see any M&A opportunities that make sense for CIBC",
            "answer3": "We're very focused on organic growth. We don't feel we need M&A to compete effectively. We'd look at opportunities that strengthen our Canadian franchise."
        })
    elif bank_id == "NA":
        qa_context.update({
            "question1": "Can you provide an update on the Canadian Western Bank acquisition",
            "answer1": "We're excited about this transaction. Regulatory approvals are progressing. CWB adds scale in Western Canada and diversifies our geographic exposure.",
            "followup1": "What are the synergy expectations",
            "followup_answer1": "We've identified meaningful cost synergies primarily in corporate functions and technology. Revenue synergies from product cross-sell are also mapped out.",
            "question2": "Your ROE continues to lead the industry - what's sustainable going forward",
            "answer2": "Our ROE reflects our leading Quebec position, efficient operations, and disciplined capital allocation. We see no reason that should change.",
            "followup2": "on your geographic expansion, how do you compete outside Quebec",
            "followup_answer2": "We're selective. We focus on commercial banking where relationships matter. We've had success winning clients who appreciate our service model.",
            "question3": "can you discuss the competitive environment in Quebec",
            "answer3": "Quebec remains our fortress. We have relationships going back generations. Competitors have tried to gain share with limited success."
        })

    qa_content = QA_TEMPLATES[bank_id].format(**qa_context)

    return md_content, qa_content


def generate_all_data():
    """Generate all mock data files."""
    random.seed(42)  # For reproducibility

    transcripts = []
    financials = []
    stock_prices = []

    for period_idx, period in enumerate(PERIODS):
        for bank_id in BANKS:
            # Generate metrics
            metrics = generate_metrics(bank_id, period_idx)

            # Generate transcripts
            md_content, qa_content = generate_transcript_content(bank_id, period, metrics)
            transcripts.append({
                "bank_id": bank_id,
                "fiscal_year": period["fiscal_year"],
                "fiscal_quarter": period["fiscal_quarter"],
                "call_date": period["call_date"],
                "sections": {
                    "management_discussion": md_content,
                    "qa": qa_content
                }
            })

            # Add to financials list
            financials.append({
                "bank_id": bank_id,
                "fiscal_year": period["fiscal_year"],
                "fiscal_quarter": period["fiscal_quarter"],
                "metrics": metrics
            })

            # Generate stock price
            stock_data = generate_stock_price(bank_id, period_idx)
            stock_prices.append({
                "bank_id": bank_id,
                "fiscal_year": period["fiscal_year"],
                "fiscal_quarter": period["fiscal_quarter"],
                "period_end_date": period["period_end"],
                **stock_data
            })

    # Write files to data directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(DATA_DIR / "transcripts.json", "w") as f:
        json.dump(transcripts, f, indent=2)
    print(f"  Generated {len(transcripts)} transcript records")

    with open(DATA_DIR / "financials.json", "w") as f:
        json.dump(financials, f, indent=2)
    print(f"  Generated {len(financials)} financial records ({len(financials) * 25} metrics)")

    with open(DATA_DIR / "stock_prices.json", "w") as f:
        json.dump(stock_prices, f, indent=2)
    print(f"  Generated {len(stock_prices)} stock price records")


def main():
    print("\n=== Mock Data Generator ===\n")
    print(f"Generating data for {len(PERIODS)} quarters across {len(BANKS)} banks...\n")
    generate_all_data()
    print("\n=== Generation complete ===\n")


if __name__ == "__main__":
    main()
