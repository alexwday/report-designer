-- subsection_versions.sql
-- Version history for subsection content iterations
-- Every generation/edit creates a new version

CREATE TABLE IF NOT EXISTS subsection_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subsection_id UUID NOT NULL REFERENCES subsections(id) ON DELETE CASCADE,

    -- Version number (auto-increment per subsection)
    version_number INTEGER NOT NULL,

    -- Snapshot of state at this version
    instructions TEXT,
    notes TEXT,
    content TEXT,
    content_type TEXT DEFAULT 'markdown',

    -- Generation metadata
    generated_by TEXT DEFAULT 'agent' CHECK (generated_by IN ('agent', 'user_edit', 'import')),
    generation_context JSONB,

    -- Flags
    is_final BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure unique version numbers per subsection
    UNIQUE(subsection_id, version_number)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_versions_subsection ON subsection_versions(subsection_id);
CREATE INDEX IF NOT EXISTS idx_versions_number ON subsection_versions(subsection_id, version_number DESC);
CREATE INDEX IF NOT EXISTS idx_versions_final ON subsection_versions(subsection_id, is_final) WHERE is_final = TRUE;
