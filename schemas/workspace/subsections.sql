-- subsections.sql
-- Content areas within sections
-- Subsections stack vertically within a section (labeled A, B, C based on position)
-- Each subsection has an optional title, notes, instructions, content, and version history

CREATE TABLE IF NOT EXISTS subsections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id UUID NOT NULL REFERENCES sections(id) ON DELETE CASCADE,

    -- Optional title for this subsection
    title TEXT,

    -- Position within section (1=A, 2=B, 3=C, etc.)
    position INTEGER NOT NULL DEFAULT 1,

    -- Content type
    widget_type TEXT NOT NULL DEFAULT 'summary'
        CHECK (widget_type IN ('summary', 'key_points', 'table', 'chart', 'comparison', 'custom')),

    -- Data source configuration (JSON for flexibility)
    -- Example: {"source_id": "financials", "method_id": "by_quarter", "parameters": {"bank_id": "RY", "fiscal_year": 2025}}
    data_source_config JSONB,

    -- Notes: Informal collaboration context (editable by user and agent)
    -- Example: "User prefers executive-friendly tone. Tried table format, user preferred bullets."
    notes TEXT,

    -- Instructions: Formal generation prompt (editable by user and agent)
    -- Example: "Summarize top 5 credit risks in 3 bullet points. Include QoQ comparison."
    instructions TEXT,

    -- Current content (latest generated/edited content)
    content TEXT,
    content_type TEXT DEFAULT 'markdown' CHECK (content_type IN ('text', 'markdown', 'html', 'json')),

    -- Version tracking (current version number, incremented on each save)
    version_number INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure unique ordering within section
    UNIQUE(section_id, position)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_subsections_section ON subsections(section_id);
CREATE INDEX IF NOT EXISTS idx_subsections_position ON subsections(section_id, position);

-- Trigger to auto-update updated_at
DROP TRIGGER IF EXISTS update_subsections_updated_at ON subsections;
CREATE TRIGGER update_subsections_updated_at
    BEFORE UPDATE ON subsections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
