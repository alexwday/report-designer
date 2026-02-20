-- Template Versions Schema
-- Stores snapshots of templates for versioning/restore functionality

CREATE TABLE IF NOT EXISTS template_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    snapshot JSONB NOT NULL,  -- Full snapshot of sections, subsections, versions
    created_by TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(template_id, version_number)
);

-- Index for listing versions by template
CREATE INDEX IF NOT EXISTS idx_template_versions_template_id
ON template_versions(template_id, version_number DESC);

-- Add is_shared column to templates for shared template browser
ALTER TABLE templates ADD COLUMN IF NOT EXISTS is_shared BOOLEAN DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_templates_is_shared ON templates(is_shared) WHERE is_shared = TRUE;
