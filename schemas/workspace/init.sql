-- init.sql
-- Initialize all workspace tables in correct dependency order
-- Run: psql -d report_designer -f schemas/workspace/init.sql

-- Note: Run templates.sql first as it defines the update_updated_at_column function
\ir templates.sql
\ir conversations.sql
\ir sections.sql
\ir subsections.sql
\ir subsection_versions.sql
\ir data_source_registry.sql
\ir uploads.sql
\ir template_versions.sql
\ir generation_presets.sql

-- Verify tables created
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
    'templates',
    'conversations',
    'messages',
    'sections',
    'subsections',
    'subsection_versions',
    'data_source_registry',
    'uploads',
    'template_versions',
    'template_generation_presets'
)
ORDER BY table_name;
