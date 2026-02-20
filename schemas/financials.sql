-- Financials Table
-- Supplementary financial metrics for Canadian Big 6 banks
-- One row per metric per bank per period

CREATE TABLE IF NOT EXISTS financials (
    id TEXT PRIMARY KEY,

    -- Filters
    bank_id TEXT NOT NULL CHECK (bank_id IN ('RY', 'TD', 'BMO', 'BNS', 'CM', 'NA')),
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter TEXT NOT NULL CHECK (fiscal_quarter IN ('Q1', 'Q2', 'Q3', 'Q4')),
    metric_id TEXT NOT NULL,

    -- Content
    metric_name TEXT NOT NULL,
    value DECIMAL,
    unit TEXT,                      -- 'CAD', 'percent', 'ratio', 'bps'
    formatted_value TEXT,           -- '$1.2B', '15.3%', etc.

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),

    -- Ensure one metric per bank/period
    UNIQUE(bank_id, fiscal_year, fiscal_quarter, metric_id)
);

-- Indexes for filtering
CREATE INDEX IF NOT EXISTS idx_financials_bank ON financials(bank_id);
CREATE INDEX IF NOT EXISTS idx_financials_period ON financials(fiscal_year, fiscal_quarter);
CREATE INDEX IF NOT EXISTS idx_financials_metric ON financials(metric_id);
CREATE INDEX IF NOT EXISTS idx_financials_bank_period ON financials(bank_id, fiscal_year, fiscal_quarter);
