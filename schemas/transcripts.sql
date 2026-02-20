-- Transcripts Table
-- Earnings call transcripts for Canadian Big 6 banks
-- Two sections per transcript: management discussion and Q&A

CREATE TABLE IF NOT EXISTS transcripts (
    id TEXT PRIMARY KEY,

    -- Filters
    bank_id TEXT NOT NULL CHECK (bank_id IN ('RY', 'TD', 'BMO', 'BNS', 'CM', 'NA')),
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter TEXT NOT NULL CHECK (fiscal_quarter IN ('Q1', 'Q2', 'Q3', 'Q4')),
    section TEXT NOT NULL CHECK (section IN ('management_discussion', 'qa')),

    -- Content
    content_text TEXT NOT NULL,

    -- Metadata
    call_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),

    -- Ensure one section per bank/period
    UNIQUE(bank_id, fiscal_year, fiscal_quarter, section)
);

-- Indexes for filtering
CREATE INDEX IF NOT EXISTS idx_transcripts_bank ON transcripts(bank_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_period ON transcripts(fiscal_year, fiscal_quarter);
CREATE INDEX IF NOT EXISTS idx_transcripts_section ON transcripts(section);
CREATE INDEX IF NOT EXISTS idx_transcripts_bank_period ON transcripts(bank_id, fiscal_year, fiscal_quarter);
