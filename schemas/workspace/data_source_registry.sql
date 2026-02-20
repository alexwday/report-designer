-- data_source_registry.sql
-- Registry of available data sources for report generation
-- Managed by data team, consumed by agent and UI

CREATE TABLE IF NOT EXISTS data_source_registry (
    id TEXT PRIMARY KEY,

    -- Display
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,

    -- Retrieval configuration (JSON for flexibility)
    retrieval_methods JSONB NOT NULL,

    -- Agent hints
    suggested_widgets JSONB,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_registry_category ON data_source_registry(category);
CREATE INDEX IF NOT EXISTS idx_registry_active ON data_source_registry(is_active) WHERE is_active = TRUE;

-- Trigger to auto-update updated_at
DROP TRIGGER IF EXISTS update_registry_updated_at ON data_source_registry;
CREATE TRIGGER update_registry_updated_at
    BEFORE UPDATE ON data_source_registry
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
