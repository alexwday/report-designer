"""
Test script for retrievers.

Tests all three retrievers against the Postgres database.
Run from project root: python scripts/test/test_retrievers.py
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.retrievers.transcripts import search_transcripts
from src.retrievers.financials import search_financials
from src.retrievers.stock_prices import search_stock_prices


def test_transcripts():
    """Test transcript retriever."""
    print("\n" + "="*60)
    print("TEST: search_transcripts")
    print("="*60)

    # Test 1: Single bank, single section
    print("\n1. Single bank (RY), Q1 2025, management_discussion only:")
    results = search_transcripts(
        queries=[{"bank_id": "RY", "fiscal_year": 2025, "fiscal_quarter": "Q1"}],
        section="management_discussion"
    )
    for r in results:
        print(f"   Bank: {r['bank_name']}")
        print(f"   Period: {r['period']}")
        print(f"   Section: {r.get('section', 'N/A')}")
        print(f"   Content length: {r.get('content_length', 0)} chars")
        if 'content' in r:
            print(f"   Preview: {r['content'][:100]}...")

    # Test 2: Multiple banks, both sections
    print("\n2. Multiple banks (RY, TD, BMO), Q1 2025, both sections:")
    results = search_transcripts(
        queries=[
            {"bank_id": "RY", "fiscal_year": 2025, "fiscal_quarter": "Q1"},
            {"bank_id": "TD", "fiscal_year": 2025, "fiscal_quarter": "Q1"},
            {"bank_id": "BMO", "fiscal_year": 2025, "fiscal_quarter": "Q1"},
        ],
        section="both"
    )
    for r in results:
        print(f"   {r['bank_id']}: {r.get('content_length', 0)} chars total")

    # Test 3: Multiple periods for one bank
    print("\n3. Single bank (NA) across multiple quarters:")
    results = search_transcripts(
        queries=[
            {"bank_id": "NA", "fiscal_year": 2024, "fiscal_quarter": "Q1"},
            {"bank_id": "NA", "fiscal_year": 2024, "fiscal_quarter": "Q4"},
            {"bank_id": "NA", "fiscal_year": 2025, "fiscal_quarter": "Q1"},
        ],
        section="qa"
    )
    for r in results:
        print(f"   {r['period']}: {r.get('content_length', 0)} chars")


def test_financials():
    """Test financials retriever."""
    print("\n" + "="*60)
    print("TEST: search_financials")
    print("="*60)

    # Test 1: Single bank, specific metrics
    print("\n1. Single bank (RY), Q1 2025, key profitability metrics:")
    results = search_financials(
        queries=[{"bank_id": "RY", "fiscal_year": 2025, "fiscal_quarter": "Q1"}],
        metrics=["net_income", "diluted_eps", "roe", "cet1_ratio"]
    )
    for r in results:
        print(f"   Bank: {r['bank_name']}")
        print(f"   Period: {r['period']}")
        for m in r.get('metrics', []):
            print(f"   - {m['name']}: {m['formatted']}")

    # Test 2: Compare banks on specific metric
    print("\n2. Compare all Big 6 banks - Net Income Q1 2025:")
    results = search_financials(
        queries=[
            {"bank_id": "RY", "fiscal_year": 2025, "fiscal_quarter": "Q1"},
            {"bank_id": "TD", "fiscal_year": 2025, "fiscal_quarter": "Q1"},
            {"bank_id": "BMO", "fiscal_year": 2025, "fiscal_quarter": "Q1"},
            {"bank_id": "BNS", "fiscal_year": 2025, "fiscal_quarter": "Q1"},
            {"bank_id": "CM", "fiscal_year": 2025, "fiscal_quarter": "Q1"},
            {"bank_id": "NA", "fiscal_year": 2025, "fiscal_quarter": "Q1"},
        ],
        metrics=["net_income"]
    )
    for r in results:
        if r.get('metrics'):
            print(f"   {r['bank_id']}: {r['metrics'][0]['formatted']}")

    # Test 3: All metrics for one bank
    print("\n3. All 25 metrics for BMO Q4 2024:")
    results = search_financials(
        queries=[{"bank_id": "BMO", "fiscal_year": 2024, "fiscal_quarter": "Q4"}],
        metrics=None  # All metrics
    )
    for r in results:
        print(f"   Bank: {r['bank_name']}, Period: {r['period']}")
        print(f"   Metrics returned: {r['metrics_count']}")


def test_stock_prices():
    """Test stock prices retriever."""
    print("\n" + "="*60)
    print("TEST: search_stock_prices")
    print("="*60)

    # Test 1: Single bank
    print("\n1. Single bank (RY) Q1 2025:")
    results = search_stock_prices(
        queries=[{"bank_id": "RY", "fiscal_year": 2025, "fiscal_quarter": "Q1"}]
    )
    for r in results:
        print(f"   Bank: {r['bank_name']} ({r['ticker']})")
        print(f"   Period: {r['period']}")
        print(f"   Close Price: ${r['close_price']:.2f}")
        print(f"   QoQ Change: {r['qoq_change_pct']:+.1f}%")
        print(f"   YoY Change: {r['yoy_change_pct']:+.1f}%")

    # Test 2: Compare all banks
    print("\n2. Compare all Big 6 banks Q1 2025:")
    results = search_stock_prices(
        queries=[
            {"bank_id": "RY", "fiscal_year": 2025, "fiscal_quarter": "Q1"},
            {"bank_id": "TD", "fiscal_year": 2025, "fiscal_quarter": "Q1"},
            {"bank_id": "BMO", "fiscal_year": 2025, "fiscal_quarter": "Q1"},
            {"bank_id": "BNS", "fiscal_year": 2025, "fiscal_quarter": "Q1"},
            {"bank_id": "CM", "fiscal_year": 2025, "fiscal_quarter": "Q1"},
            {"bank_id": "NA", "fiscal_year": 2025, "fiscal_quarter": "Q1"},
        ]
    )
    print(f"   {'Bank':<6} {'Price':>10} {'QoQ':>8} {'YoY':>8}")
    print(f"   {'-'*6} {'-'*10} {'-'*8} {'-'*8}")
    for r in results:
        print(f"   {r['bank_id']:<6} ${r['close_price']:>8.2f} {r['qoq_change_pct']:>+7.1f}% {r['yoy_change_pct']:>+7.1f}%")

    # Test 3: Track one bank over time
    print("\n3. TD Bank price trend FY2024-2025:")
    results = search_stock_prices(
        queries=[
            {"bank_id": "TD", "fiscal_year": 2024, "fiscal_quarter": "Q1"},
            {"bank_id": "TD", "fiscal_year": 2024, "fiscal_quarter": "Q2"},
            {"bank_id": "TD", "fiscal_year": 2024, "fiscal_quarter": "Q3"},
            {"bank_id": "TD", "fiscal_year": 2024, "fiscal_quarter": "Q4"},
            {"bank_id": "TD", "fiscal_year": 2025, "fiscal_quarter": "Q1"},
        ]
    )
    for r in results:
        print(f"   {r['period']}: ${r['close_price']:.2f} (QoQ: {r['qoq_change_pct']:+.1f}%)")


def main():
    print("\n" + "="*60)
    print("REPORT DESIGNER - RETRIEVER TESTS")
    print("="*60)

    try:
        test_transcripts()
        test_financials()
        test_stock_prices()

        print("\n" + "="*60)
        print("ALL TESTS PASSED")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
