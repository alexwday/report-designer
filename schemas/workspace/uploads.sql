-- File uploads table for Report Designer
-- Stores metadata and extracted text from uploaded documents

CREATE TABLE IF NOT EXISTS uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES templates(id) ON DELETE CASCADE,

    -- File metadata
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    content_type TEXT,
    size_bytes INTEGER,

    -- Extracted content for AI reference
    extracted_text TEXT,
    extraction_status TEXT DEFAULT 'pending', -- pending, completed, failed
    extraction_error TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for quick lookup by template
CREATE INDEX IF NOT EXISTS idx_uploads_template_id ON uploads(template_id);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_uploads_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS uploads_updated_at ON uploads;
CREATE TRIGGER uploads_updated_at
    BEFORE UPDATE ON uploads
    FOR EACH ROW
    EXECUTE FUNCTION update_uploads_updated_at();
