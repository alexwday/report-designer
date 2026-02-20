-- Stock Prices Table
-- End-of-period stock prices for Canadian Big 6 banks
-- One row per bank per period with precalculated changes

CREATE TABLE IF NOT EXISTS stock_prices (
    id TEXT PRIMARY KEY,

    -- Filters
    bank_id TEXT NOT NULL CHECK (bank_id IN ('RY', 'TD', 'BMO', 'BNS', 'CM', 'NA')),
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter TEXT NOT NULL CHECK (fiscal_quarter IN ('Q1', 'Q2', 'Q3', 'Q4')),

    -- Content
    close_price DECIMAL,            -- End of period closing price (CAD)
    qoq_change_pct DECIMAL,         -- Quarter-over-quarter % change
    yoy_change_pct DECIMAL,         -- Year-over-year % change

    -- Metadata
    period_end_date DATE,           -- Last trading day of the quarter
    created_at TIMESTAMP DEFAULT NOW(),

    -- Ensure one record per bank/period
    UNIQUE(bank_id, fiscal_year, fiscal_quarter)
);

-- Indexes for filtering
CREATE INDEX IF NOT EXISTS idx_stock_bank ON stock_prices(bank_id);
CREATE INDEX IF NOT EXISTS idx_stock_period ON stock_prices(fiscal_year, fiscal_quarter);
CREATE INDEX IF NOT EXISTS idx_stock_bank_period ON stock_prices(bank_id, fiscal_year, fiscal_quarter);
