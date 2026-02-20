"""
Workspace management tools for Report Designer.

Provides MCP tools for managing templates, sections, subsections,
conversations, and data sources.
"""

from .templates import (
    get_template,
    create_template,
    update_template,
    delete_template,
    list_templates,
    TOOL_DEFINITIONS as TEMPLATE_TOOLS,
)
from .sections import (
    get_sections,
    create_section,
    update_section,
    delete_section,
    TOOL_DEFINITIONS as SECTION_TOOLS,
)
from .subsections import (
    get_subsection,
    get_version,
    create_subsection,
    update_title as update_subsection_title,
    reorder_subsection,
    delete_subsection,
    update_notes,
    update_instructions,
    configure_subsection,
    save_subsection_version,
    TOOL_DEFINITIONS as SUBSECTION_TOOLS,
)
from .data_sources import (
    get_data_sources,
    TOOL_DEFINITION as DATA_SOURCES_TOOL,
)
from .conversations import (
    get_or_create_conversation,
    add_message,
    get_conversation_history,
    get_messages_for_openai,
)
from .template_versions import (
    create_version as create_template_version,
    list_versions as list_template_versions,
    get_version as get_template_version,
    restore_version as restore_template_version,
    fork_template,
    list_shared_templates,
    set_template_shared,
)
from .generation_presets import (
    get_template_generation_preset,
    save_template_generation_preset,
)

__all__ = [
    # Templates
    "get_template",
    "create_template",
    "update_template",
    "delete_template",
    "list_templates",
    "TEMPLATE_TOOLS",
    # Sections
    "get_sections",
    "create_section",
    "update_section",
    "delete_section",
    "SECTION_TOOLS",
    # Subsections
    "get_subsection",
    "get_version",
    "create_subsection",
    "update_subsection_title",
    "reorder_subsection",
    "delete_subsection",
    "update_notes",
    "update_instructions",
    "configure_subsection",
    "save_subsection_version",
    "SUBSECTION_TOOLS",
    # Data sources
    "get_data_sources",
    "DATA_SOURCES_TOOL",
    # Conversations
    "get_or_create_conversation",
    "add_message",
    "get_conversation_history",
    "get_messages_for_openai",
    # Template versions
    "create_template_version",
    "list_template_versions",
    "get_template_version",
    "restore_template_version",
    "fork_template",
    "list_shared_templates",
    "set_template_shared",
    # Generation presets
    "get_template_generation_preset",
    "save_template_generation_preset",
]
