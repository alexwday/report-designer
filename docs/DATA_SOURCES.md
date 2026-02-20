# Data Sources Guide - Big 6 Canadian Banks Q1 2025

## Overview

This document provides links and guidance for manually downloading Q1 2025 data for the Big 6 Canadian banks. All banks report quarterly results in late February (for Q1 ending January 31).

**Note:** Canadian banks have fiscal years ending October 31, so Q1 = Nov-Jan.

---

## 1. Royal Bank of Canada (RY)

**Investor Relations:** https://www.rbc.com/investor-relations/

### Supplementary Financials
- **Q1 2025 Supplementary Financial Information:** https://www.rbc.com/investor-relations/_assets-custom/pdf/25q1supp.pdf
- **Q1 2025 Report to Shareholders:** https://www.rbc.com/investor-relations/_assets-custom/pdf/2025q1_report.pdf
- **Q1 2025 Investor Presentation:** https://www.rbc.com/investor-relations/_assets-custom/pdf/irdeck2025q1.pdf
- **Q1 2025 Earnings Release:** https://www.rbc.com/investor-relations/_assets-custom/pdf/2025q1release.pdf

### Transcripts
- **Seeking Alpha Transcript:** https://seekingalpha.com/article/4762848-royal-bank-of-canada-ry-q1-2025-earnings-call-transcript
- No official PDF transcript found on RBC IR site

---

## 2. Toronto-Dominion Bank (TD)

**Investor Relations:** https://www.td.com/ca/en/about-td/for-investors/investor-relations

### Supplementary Financials
- **Q1 2025 Supplementary Financial Information:** https://www.td.com/content/dam/tdcom/canada/about-td/pdf/quarterly-results/2025/q1/2025-q1-sfi-en.pdf (inferred from naming pattern)
- **Q1 2025 Report to Shareholders:** https://www.td.com/content/dam/tdcom/canada/about-td/pdf/quarterly-results/2025/q1/2025-q1-reports-shareholders-en.pdf
- **Q1 2025 Earnings News Release:** https://www.td.com/content/dam/tdcom/canada/about-td/pdf/quarterly-results/2025/q1/2025-q1-earnings-newsrelease-en.pdf
- **Q1 2025 Investor Fact Sheet:** https://www.td.com/content/dam/tdcom/canada/about-td/pdf/quarterly-results/2025/q1/2025-q1-investor-facts-sheet-f-en.pdf

### Transcripts
- **Seeking Alpha Transcript:** https://seekingalpha.com/article/4762804-the-toronto-dominion-bank-td-q1-2025-earnings-call-transcript
- **Yahoo Finance Transcript:** https://finance.yahoo.com/quote/TD.TO/earnings/TD.TO-Q1-2025-earnings_call-266213.html

---

## 3. Bank of Montreal (BMO)

**Investor Relations:** https://www.bmo.com/main/about-bmo/banking/investor-relations/financial-information

### Supplementary Financials
- **Q1 2025 Supplementary Financial Information:** https://www.bmo.com/ir/qtrinfo/1/2025-q1/Suppq125.pdf (inferred from naming pattern)
- **Q1 2025 Report to Shareholders:** https://www.bmo.com/ir/qtrinfo/1/2025-q1/Q125_ReportToShareholders.pdf
- **Q1 2025 Analyst Presentation:** https://www.bmo.com/ir/qtrinfo/1/2025-q1/Q125_AnalystPresentation.pdf

### Transcripts
- Available via Seeking Alpha and third-party services
- No official PDF transcript found on BMO IR site

---

## 4. Bank of Nova Scotia / Scotiabank (BNS)

**Investor Relations:** https://www.scotiabank.com/ca/en/about/investors-shareholders.html
**Financial Results:** https://www.scotiabank.com/ca/en/about/investors-shareholders/financial-result.html

### Supplementary Financials
- **Q1 2025 Supplementary Regulatory Capital Disclosures:** https://www.scotiabank.com/content/dam/scotiabank/corporate/quarterly-reports/2025/q1/Q125_Supplementary_Regulatory_Capital_Disclosures-EN.pdf
- Look for "Supplementary Financial Information" on the Financial Results page

### Transcripts
- **Q1 2025 Earnings Call Transcript (Official PDF):** https://www.scotiabank.com/content/dam/scotiabank/corporate/quarterly-reports/2025/q1/BNS-T_Transcript_2025-02-25.pdf

**Note:** Scotiabank is the only bank that provides an official PDF transcript on their IR site.

---

## 5. Canadian Imperial Bank of Commerce (CM / CIBC)

**Investor Relations:** https://www.cibc.com/en/about-cibc/investor-relations.html
**Quarterly Results:** https://www.cibc.com/en/about-cibc/investor-relations/quarterly-results.html

### Supplementary Financials
- **Q1 2025 Supplementary Financial Information:** https://www.cibc.com/content/dam/cibc-public-assets/about-cibc/investor-relations/pdfs/quarterly-results/2025/q125financials-en.pdf
- **Q1 2025 Investor Fact Sheet:** https://www.cibc.com/content/dam/cibc-public-assets/about-cibc/investor-relations/pdfs/quarterly-results/2025/q125factsheet-en.pdf

### Transcripts
- Available via Seeking Alpha and third-party services
- No official PDF transcript found on CIBC IR site

---

## 6. National Bank of Canada (NA)

**Investor Relations:** https://www.nbc.ca/about-us/investors.html
**Quarterly Results:** https://www.nbc.ca/about-us/investors/quarterly-results.html

### Supplementary Financials
- **Supplementary Financial Information** available on the Quarterly Results page
- **Supplementary Regulatory Capital and Pillar 3 Disclosure** also available

### Transcripts
- **Seeking Alpha Transcripts:** https://seekingalpha.com/symbol/NTIOF/earnings/transcripts
- Report to Shareholders and slide presentation available on IR page

---

## Stock Prices (All Banks)

Stock prices can be automated using Yahoo Finance. Tickers on TSX:
- RY.TO (Royal Bank)
- TD.TO (TD Bank)
- BMO.TO (Bank of Montreal)
- BNS.TO (Scotiabank)
- CM.TO (CIBC)
- NA.TO (National Bank)

**Note:** Can use `yfinance` Python package to pull historical data programmatically.

---

## Summary - What to Download

### Transcripts (Manual)
| Bank | Source | Notes |
|------|--------|-------|
| RY | Seeking Alpha | Copy/paste or subscribe |
| TD | Seeking Alpha / Yahoo Finance | Copy/paste or subscribe |
| BMO | Seeking Alpha | Copy/paste or subscribe |
| BNS | **Official PDF** | Direct download from IR site |
| CM | Seeking Alpha | Copy/paste or subscribe |
| NA | Seeking Alpha | Copy/paste or subscribe |

### Supplementary Financials (Manual)
| Bank | Document | Direct Link |
|------|----------|-------------|
| RY | Supplementary Financial Info | Direct PDF available |
| TD | Supplementary Financial Info | Check IR quarterly results page |
| BMO | Supplementary Financial Info | Pattern: Suppq125.pdf |
| BNS | Supplementary Regulatory Capital | Direct PDF available |
| CM | Supplementary Financial Info | Direct PDF available |
| NA | Supplementary Financial Info | Check IR quarterly results page |

### Stock Prices (Automated)
Can be pulled via Yahoo Finance API using `yfinance` package:
```python
import yfinance as yf
tickers = ['RY.TO', 'TD.TO', 'BMO.TO', 'BNS.TO', 'CM.TO', 'NA.TO']
```

---

## Q1 2025 Earnings Dates (All February 2025)

| Bank | Earnings Date |
|------|---------------|
| BNS | February 25, 2025 |
| BMO | February 25, 2025 |
| TD | February 27, 2025 |
| RY | February 27, 2025 |
| CM | February 27, 2025 |
| NA | February 26, 2025 |
