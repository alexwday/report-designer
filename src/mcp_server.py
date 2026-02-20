"""
MCP Server for Report Designer

Exposes tools for:
1. Data retrieval (bank transcripts, financials, stock prices)
2. Workspace management (templates, sections, subsections)
3. Data source registry

Usage:
    python -m src.mcp_server

Or configure in Claude Desktop's MCP settings.
"""

import asyncio
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Data retrieval tools
from .retrievers.transcripts import (
    search_transcripts,
    TOOL_DEFINITION as TRANSCRIPTS_TOOL,
)
from .retrievers.financials import (
    search_financials,
    TOOL_DEFINITION as FINANCIALS_TOOL,
)
from .retrievers.stock_prices import (
    search_stock_prices,
    TOOL_DEFINITION as STOCK_PRICES_TOOL,
)

# Workspace management tools
from .workspace.templates import (
    get_template,
    create_template,
    update_template,
    list_templates,
    TOOL_DEFINITIONS as TEMPLATE_TOOLS,
)
from .workspace.sections import (
    get_sections,
    create_section,
    update_section,
    delete_section,
    TOOL_DEFINITIONS as SECTION_TOOLS,
)
from .workspace.subsections import (
    get_subsection,
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
from .workspace.data_sources import (
    get_data_sources,
    TOOL_DEFINITION as DATA_SOURCES_TOOL,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server
server = Server("report-designer")


def _build_tool_list() -> list[Tool]:
    """Build the list of all available tools."""
    tools = []

    # Data retrieval tools
    for tool_def in [TRANSCRIPTS_TOOL, FINANCIALS_TOOL, STOCK_PRICES_TOOL]:
        tools.append(Tool(
            name=tool_def["name"],
            description=tool_def["description"],
            inputSchema=tool_def["inputSchema"],
        ))

    # Template tools
    for tool_def in TEMPLATE_TOOLS.values():
        tools.append(Tool(
            name=tool_def["name"],
            description=tool_def["description"],
            inputSchema=tool_def["inputSchema"],
        ))

    # Section tools
    for tool_def in SECTION_TOOLS.values():
        tools.append(Tool(
            name=tool_def["name"],
            description=tool_def["description"],
            inputSchema=tool_def["inputSchema"],
        ))

    # Subsection tools
    for tool_def in SUBSECTION_TOOLS.values():
        tools.append(Tool(
            name=tool_def["name"],
            description=tool_def["description"],
            inputSchema=tool_def["inputSchema"],
        ))

    # Data source registry tool
    tools.append(Tool(
        name=DATA_SOURCES_TOOL["name"],
        description=DATA_SOURCES_TOOL["description"],
        inputSchema=DATA_SOURCES_TOOL["inputSchema"],
    ))

    return tools


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return _build_tool_list()


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    logger.info(f"Tool called: {name} with arguments: {arguments}")

    try:
        # Data retrieval tools
        if name == "search_transcripts":
            results = search_transcripts(
                queries=arguments["queries"],
                section=arguments.get("section", "both"),
            )
        elif name == "search_financials":
            results = search_financials(
                queries=arguments["queries"],
                metrics=arguments.get("metrics"),
            )
        elif name == "search_stock_prices":
            results = search_stock_prices(
                queries=arguments["queries"],
            )

        # Template tools
        elif name == "get_template":
            results = get_template(
                template_id=arguments["template_id"],
            )
        elif name == "create_template":
            results = create_template(
                name=arguments["name"],
                created_by=arguments["created_by"],
                description=arguments.get("description"),
                output_format=arguments.get("output_format", "pdf"),
                orientation=arguments.get("orientation", "landscape"),
            )
        elif name == "update_template":
            results = update_template(
                template_id=arguments["template_id"],
                name=arguments.get("name"),
                description=arguments.get("description"),
                output_format=arguments.get("output_format"),
                orientation=arguments.get("orientation"),
                status=arguments.get("status"),
            )
        elif name == "list_templates":
            results = list_templates(
                created_by=arguments.get("created_by"),
                status=arguments.get("status"),
                limit=arguments.get("limit", 50),
            )

        # Section tools
        elif name == "get_sections":
            results = get_sections(
                template_id=arguments["template_id"],
                include_content=arguments.get("include_content", False),
            )
        elif name == "create_section":
            results = create_section(
                template_id=arguments["template_id"],
                title=arguments.get("title"),
                position=arguments.get("position"),
            )
        elif name == "update_section":
            results = update_section(
                section_id=arguments["section_id"],
                title=arguments.get("title"),
                position=arguments.get("position"),
            )
        elif name == "delete_section":
            results = delete_section(
                section_id=arguments["section_id"],
            )

        # Subsection tools
        elif name == "get_subsection":
            results = get_subsection(
                subsection_id=arguments["subsection_id"],
                include_versions=arguments.get("include_versions", True),
                version_limit=arguments.get("version_limit", 10),
            )
        elif name == "create_subsection":
            results = create_subsection(
                section_id=arguments["section_id"],
                title=arguments.get("title"),
                position=arguments.get("position"),
            )
        elif name == "update_subsection_title":
            results = update_subsection_title(
                subsection_id=arguments["subsection_id"],
                title=arguments["title"],
            )
        elif name == "reorder_subsection":
            results = reorder_subsection(
                subsection_id=arguments["subsection_id"],
                new_position=arguments["new_position"],
            )
        elif name == "delete_subsection":
            results = delete_subsection(
                subsection_id=arguments["subsection_id"],
            )
        elif name == "update_notes":
            results = update_notes(
                subsection_id=arguments["subsection_id"],
                notes=arguments["notes"],
                append=arguments.get("append", False),
            )
        elif name == "update_instructions":
            results = update_instructions(
                subsection_id=arguments["subsection_id"],
                instructions=arguments["instructions"],
            )
        elif name == "configure_subsection":
            configure_args = {
                "subsection_id": arguments["subsection_id"],
            }
            if "widget_type" in arguments:
                configure_args["widget_type"] = arguments.get("widget_type")
            if "data_source_config" in arguments:
                configure_args["data_source_config"] = arguments.get("data_source_config")
            results = configure_subsection(**configure_args)
        elif name == "save_subsection_version":
            results = save_subsection_version(
                subsection_id=arguments["subsection_id"],
                content=arguments["content"],
                content_type=arguments.get("content_type", "markdown"),
                generated_by=arguments.get("generated_by", "agent"),
                is_final=arguments.get("is_final", False),
                generation_context=arguments.get("generation_context"),
                title=arguments.get("title"),
            )

        # Data source registry
        elif name == "get_data_sources":
            results = get_data_sources(
                category=arguments.get("category"),
                active_only=arguments.get("active_only", True),
            )

        else:
            raise ValueError(f"Unknown tool: {name}")

        # Format results as JSON
        result_text = json.dumps(results, indent=2, default=str)
        result_count = len(results) if isinstance(results, list) else 1
        logger.info(f"Tool {name} returned {result_count} result(s)")

        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        import traceback
        traceback.print_exc()
        error_response = {"error": str(e)}
        return [TextContent(type="text", text=json.dumps(error_response))]


async def main():
    """Run the MCP server."""
    logger.info("Starting Report Designer MCP Server...")
    tools = _build_tool_list()
    logger.info(f"Registered {len(tools)} tools: {[t.name for t in tools]}")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
