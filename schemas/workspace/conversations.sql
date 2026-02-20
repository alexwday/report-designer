-- conversations.sql
-- Persistent conversation history for template workspaces
-- All chat interactions feed into the same conversation

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES templates(id) ON DELETE CASCADE,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- One conversation per template
    UNIQUE(template_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,

    -- Message content
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,

    -- Context markers (for UI surfaces)
    surface TEXT NOT NULL DEFAULT 'main' CHECK (surface IN ('main', 'mini', 'agent_note')),

    -- If message relates to specific section/subsection
    section_id UUID,
    subsection_id UUID,

    -- Ordering
    sequence_number INTEGER NOT NULL,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for efficient retrieval
CREATE INDEX IF NOT EXISTS idx_conversations_template ON conversations(template_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_sequence ON messages(conversation_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_messages_section ON messages(section_id) WHERE section_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_subsection ON messages(subsection_id) WHERE subsection_id IS NOT NULL;
