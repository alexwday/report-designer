-- sections.sql
-- Document sections (can span multiple PDF pages)
-- Sections contain stacked subsections (A, B, C, etc.)

CREATE TABLE IF NOT EXISTS sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES templates(id) ON DELETE CASCADE,

    -- Identity
    title TEXT,

    -- Ordering within template
    position INTEGER NOT NULL,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure unique ordering within template
    UNIQUE(template_id, position)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sections_template ON sections(template_id);
CREATE INDEX IF NOT EXISTS idx_sections_position ON sections(template_id, position);

-- Trigger to auto-update updated_at
DROP TRIGGER IF EXISTS update_sections_updated_at ON sections;
CREATE TRIGGER update_sections_updated_at
    BEFORE UPDATE ON sections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
