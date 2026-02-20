-- generation_presets.sql
-- Stores reusable generation initialization inputs per template

CREATE TABLE IF NOT EXISTS template_generation_presets (
    template_id UUID PRIMARY KEY REFERENCES templates(id) ON DELETE CASCADE,
    run_inputs JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_template_generation_presets_updated_at
    ON template_generation_presets(updated_at DESC);
