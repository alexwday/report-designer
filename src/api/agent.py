"""
OpenAI Agent Integration for Report Designer.

Handles:
- Converting MCP tool definitions to OpenAI function format
- Building context-aware system prompts
- Executing the tool-calling loop
"""

import json
import re
from copy import deepcopy
from typing import Any, Callable

# Import all workspace functions and tool definitions
from ..workspace import (
    # Templates
    get_template,
    create_template,
    update_template,
    list_templates,
    TEMPLATE_TOOLS,
    # Sections
    get_sections,
    create_section,
    update_section,
    delete_section,
    SECTION_TOOLS,
    # Subsections
    get_subsection,
    create_subsection,
    update_subsection_title,
    reorder_subsection,
    delete_subsection,
    update_notes,
    update_instructions,
    configure_subsection,
    save_subsection_version,
    SUBSECTION_TOOLS,
    # Data sources
    get_data_sources,
    DATA_SOURCES_TOOL,
    # Conversations
    get_or_create_conversation,
    add_message,
    get_messages_for_openai,
)

# Import retrievers
from ..retrievers.transcripts import (
    search_transcripts,
    TOOL_DEFINITION as TRANSCRIPTS_TOOL,
)
from ..retrievers.financials import (
    search_financials,
    TOOL_DEFINITION as FINANCIALS_TOOL,
)
from ..retrievers.stock_prices import (
    search_stock_prices,
    TOOL_DEFINITION as STOCK_PRICES_TOOL,
)
from ..uploads import (
    list_uploads,
    get_upload_content,
    TOOL_DEFINITION as UPLOADS_TOOL,
)
from ..config.settings import get_settings
from ..infra.llm import get_openai_client

# Configuration
OPENAI_MODEL = get_settings().OPENAI_MODEL
MAX_TOOL_ITERATIONS = 10

# Initialize OpenAI client via centralized auth resolution.
client = get_openai_client()


# ============================================================
# Tool Registry
# ============================================================

TOOL_REGISTRY: dict[str, Callable] = {
    # Data retrieval
    "search_transcripts": search_transcripts,
    "search_financials": search_financials,
    "search_stock_prices": search_stock_prices,
    # Templates
    "get_template": get_template,
    "create_template": create_template,
    "update_template": update_template,
    "list_templates": list_templates,
    # Sections
    "get_sections": get_sections,
    "create_section": create_section,
    "update_section": update_section,
    "delete_section": delete_section,
    # Subsections
    "get_subsection": get_subsection,
    "create_subsection": create_subsection,
    "update_subsection_title": update_subsection_title,
    "reorder_subsection": reorder_subsection,
    "delete_subsection": delete_subsection,
    "update_notes": update_notes,
    "update_instructions": update_instructions,
    "configure_subsection": configure_subsection,
    "save_subsection_version": save_subsection_version,
    # Data sources
    "get_data_sources": get_data_sources,
    # Uploads
    "list_uploads": list_uploads,
    "get_uploaded_document": get_upload_content,
}


STRUCTURE_MUTATION_TOOLS = {
    "create_section",
    "delete_section",
    "create_subsection",
    "delete_subsection",
    "reorder_subsection",
}


def _build_tool_signature(tool_name: str, arguments: dict[str, Any]) -> str:
    """
    Build a deterministic signature for de-duplicating tool calls.

    The agent occasionally emits repeated configure_subsection calls with
    identical payloads in a single chat turn. We use a canonical JSON encoding
    of the arguments to detect those duplicates.
    """
    canonical_args = json.dumps(arguments, sort_keys=True, default=str)
    return f"{tool_name}:{canonical_args}"


def _normalize_reference_token(value: str) -> str:
    """Normalize free-form reference tokens (e.g., 'S1-A', 'section 1')."""
    return "".join(ch for ch in value.strip().lower() if ch.isalnum())


def _build_reference_maps(template_id: str) -> tuple[dict[str, str], dict[str, str]]:
    """
    Build alias -> UUID maps for section/subsection references.

    Supported aliases include:
    - Sections: 1, S1, section1
    - Subsections: 1A, S1A, S1.1, subsection1A
    """
    section_reference_map: dict[str, str] = {}
    subsection_reference_map: dict[str, str] = {}

    sections = get_sections(template_id, include_content=False)
    if not isinstance(sections, list):
        return section_reference_map, subsection_reference_map

    sorted_sections = sorted(
        (section for section in sections if isinstance(section, dict)),
        key=lambda section: section.get("position", 0),
    )

    for section in sorted_sections:
        section_id = section.get("id")
        section_position = section.get("position")
        if not isinstance(section_id, str) or not section_id:
            continue
        if not isinstance(section_position, int) or section_position < 1:
            continue

        section_aliases = [
            str(section_position),
            f"s{section_position}",
            f"section{section_position}",
        ]
        for alias in section_aliases:
            section_reference_map[_normalize_reference_token(alias)] = section_id

        subsections = section.get("subsections")
        if not isinstance(subsections, list):
            continue

        sorted_subsections = sorted(
            (subsection for subsection in subsections if isinstance(subsection, dict)),
            key=lambda subsection: subsection.get("position", 0),
        )
        for subsection in sorted_subsections:
            subsection_id = subsection.get("id")
            subsection_position = subsection.get("position")
            if not isinstance(subsection_id, str) or not subsection_id:
                continue
            if not isinstance(subsection_position, int) or subsection_position < 1:
                continue

            label = (
                chr(64 + subsection_position)
                if 1 <= subsection_position <= 26
                else str(subsection_position)
            )
            subsection_aliases = [
                f"{section_position}{label}",
                f"s{section_position}{label}",
                f"s{section_position}.{subsection_position}",
                f"subsection{section_position}{label}",
            ]
            for alias in subsection_aliases:
                subsection_reference_map[_normalize_reference_token(alias)] = subsection_id

    return section_reference_map, subsection_reference_map


def _build_primary_id_to_ref_maps(
    section_reference_map: dict[str, str],
    subsection_reference_map: dict[str, str],
) -> tuple[dict[str, str], dict[str, str]]:
    """Build canonical UUID -> reference maps (e.g., uuid -> S1 / S1A)."""
    section_id_to_ref: dict[str, str] = {}
    subsection_id_to_ref: dict[str, str] = {}

    for alias, section_id in section_reference_map.items():
        if not isinstance(alias, str) or not isinstance(section_id, str):
            continue
        if not re.fullmatch(r"s\d+", alias):
            continue
        section_id_to_ref[section_id] = alias.upper()

    for alias, subsection_id in subsection_reference_map.items():
        if not isinstance(alias, str) or not isinstance(subsection_id, str):
            continue
        if not re.fullmatch(r"s\d+[a-z]+", alias):
            continue
        subsection_id_to_ref[subsection_id] = alias.upper()

    return section_id_to_ref, subsection_id_to_ref


def _sanitize_tool_result_for_model(
    value: Any,
    section_id_to_ref: dict[str, str],
    subsection_id_to_ref: dict[str, str],
) -> Any:
    """
    Replace known UUIDs with compact refs in tool-result messages sent back to the model.

    This nudges the model to keep using short refs in subsequent tool calls, which
    improves reliability and token efficiency.
    """
    if isinstance(value, str):
        if value in subsection_id_to_ref:
            return subsection_id_to_ref[value]
        if value in section_id_to_ref:
            return section_id_to_ref[value]
        return value

    if isinstance(value, list):
        return [
            _sanitize_tool_result_for_model(item, section_id_to_ref, subsection_id_to_ref)
            for item in value
        ]

    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"section_id", "id"} and isinstance(item, str):
                if item in section_id_to_ref:
                    sanitized[key] = section_id_to_ref[item]
                    continue
                if item in subsection_id_to_ref:
                    sanitized[key] = subsection_id_to_ref[item]
                    continue
            if key == "subsection_id" and isinstance(item, str):
                if item in subsection_id_to_ref:
                    sanitized[key] = subsection_id_to_ref[item]
                    continue
            sanitized[key] = _sanitize_tool_result_for_model(
                item,
                section_id_to_ref,
                subsection_id_to_ref,
            )
        return sanitized

    return value


def _resolve_reference_value(value: Any, reference_map: dict[str, str]) -> Any:
    """Resolve integers/aliases to canonical UUIDs when possible."""
    if isinstance(value, int):
        return reference_map.get(_normalize_reference_token(str(value)), value)
    if isinstance(value, str):
        token = _normalize_reference_token(value)
        return reference_map.get(token, value)
    return value


def _normalize_tool_references(
    arguments: dict[str, Any],
    section_reference_map: dict[str, str],
    subsection_reference_map: dict[str, str],
) -> dict[str, Any]:
    """Normalize section/subsection identifiers in tool arguments."""
    normalized = deepcopy(arguments)

    if "section_id" in normalized:
        normalized["section_id"] = _resolve_reference_value(
            normalized.get("section_id"),
            section_reference_map,
        )

    if "subsection_id" in normalized:
        normalized["subsection_id"] = _resolve_reference_value(
            normalized.get("subsection_id"),
            subsection_reference_map,
        )

    data_source_config = normalized.get("data_source_config")
    if isinstance(data_source_config, dict):
        dependencies = data_source_config.get("dependencies")
        if isinstance(dependencies, dict):
            section_ids = dependencies.get("section_ids")
            if isinstance(section_ids, list):
                dependencies["section_ids"] = [
                    _resolve_reference_value(section_id, section_reference_map)
                    for section_id in section_ids
                ]
            subsection_ids = dependencies.get("subsection_ids")
            if isinstance(subsection_ids, list):
                dependencies["subsection_ids"] = [
                    _resolve_reference_value(subsection_id, subsection_reference_map)
                    for subsection_id in subsection_ids
                ]
            data_source_config["dependencies"] = dependencies
        normalized["data_source_config"] = data_source_config

    return normalized


def _method_id_from_definition(method_definition: dict[str, Any]) -> str | None:
    """Read a retrieval method identifier from registry definition variants."""
    if not isinstance(method_definition, dict):
        return None
    method_id = method_definition.get("method_id") or method_definition.get("id")
    return method_id if isinstance(method_id, str) and method_id else None


def _parameter_keys_from_method(method_definition: dict[str, Any]) -> set[str]:
    """Get parameter keys declared by a retrieval method schema."""
    keys: set[str] = set()
    parameters = method_definition.get("parameters")
    if not isinstance(parameters, list):
        return keys

    for parameter in parameters:
        if not isinstance(parameter, dict):
            continue
        key = parameter.get("key") or parameter.get("name")
        if isinstance(key, str) and key:
            keys.add(key)
    return keys


def _choose_method_from_mcp_tool(
    method_definitions: list[dict[str, Any]],
    mcp_tool_name: str,
    parameters: dict[str, Any] | None,
) -> str | None:
    """
    Choose a method_id when the model provides an MCP tool name as method_id.

    Example:
      method_id: "search_transcripts" -> by_quarter / compare_banks
    """
    lowered_mcp_tool = mcp_tool_name.strip().lower()
    matches: list[dict[str, Any]] = []
    for method_definition in method_definitions:
        if not isinstance(method_definition, dict):
            continue
        method_tool = method_definition.get("mcp_tool")
        if isinstance(method_tool, str) and method_tool.strip().lower() == lowered_mcp_tool:
            matches.append(method_definition)

    if not matches:
        return None
    if len(matches) == 1:
        return _method_id_from_definition(matches[0])

    params = parameters if isinstance(parameters, dict) else {}
    has_bank_ids = isinstance(params.get("bank_ids"), list) and len(params["bank_ids"]) > 0
    has_bank_id = isinstance(params.get("bank_id"), str) and bool(params.get("bank_id").strip())

    if has_bank_ids:
        for method_definition in matches:
            method_id = _method_id_from_definition(method_definition)
            if method_id == "compare_banks":
                return method_id
            if "bank_ids" in _parameter_keys_from_method(method_definition):
                return method_id

    if has_bank_id:
        for method_definition in matches:
            method_id = _method_id_from_definition(method_definition)
            if method_id == "by_quarter":
                return method_id
            if "bank_id" in _parameter_keys_from_method(method_definition):
                return method_id

    # Ambiguous fallback: prefer by_quarter if present, else first matching method.
    for method_definition in matches:
        method_id = _method_id_from_definition(method_definition)
        if method_id == "by_quarter":
            return method_id
    return _method_id_from_definition(matches[0])


def _normalize_data_input_identifiers(
    input_config: dict[str, Any],
    registry_by_id: dict[str, dict[str, Any]],
    source_id_lookup: dict[str, str],
    source_name_lookup: dict[str, str],
) -> None:
    """
    Normalize source_id/method_id aliases to canonical registry IDs in-place.
    """
    if not isinstance(input_config, dict):
        return

    raw_source_id = input_config.get("source_id")
    canonical_source_id: str | None = None
    if isinstance(raw_source_id, str):
        normalized_source_key = raw_source_id.strip().lower()
        canonical_source_id = source_id_lookup.get(normalized_source_key)
        if canonical_source_id is None:
            canonical_source_id = source_name_lookup.get(normalized_source_key)
        if canonical_source_id is not None:
            input_config["source_id"] = canonical_source_id

    source_id = input_config.get("source_id")
    if not isinstance(source_id, str):
        return
    source_definition = registry_by_id.get(source_id)
    if not isinstance(source_definition, dict):
        return

    method_definitions = source_definition.get("retrieval_methods")
    if not isinstance(method_definitions, list):
        return

    method_lookup: dict[str, str] = {}
    for method_definition in method_definitions:
        method_id = _method_id_from_definition(method_definition)
        if method_id:
            method_lookup[method_id.lower()] = method_id

    raw_method_id = input_config.get("method_id")
    if not isinstance(raw_method_id, str) or not raw_method_id.strip():
        return

    method_id_key = raw_method_id.strip().lower()
    canonical_method_id = method_lookup.get(method_id_key)
    if canonical_method_id:
        input_config["method_id"] = canonical_method_id
        return

    parameters = input_config.get("parameters")
    if not isinstance(parameters, dict):
        parameters = {}
        input_config["parameters"] = parameters

    # Transcript shorthand occasionally appears as method_id.
    if source_id == "transcripts" and method_id_key in {"management_discussion", "qa", "both"}:
        parameters.setdefault("section", method_id_key)
        if (
            isinstance(parameters.get("bank_ids"), list)
            and len(parameters["bank_ids"]) > 0
            and "compare_banks" in method_lookup
        ):
            input_config["method_id"] = "compare_banks"
        elif "by_quarter" in method_lookup:
            input_config["method_id"] = "by_quarter"
        return

    # Handle MCP tool-name aliases like `search_transcripts`.
    mcp_alias_method_id = _choose_method_from_mcp_tool(
        method_definitions,
        raw_method_id,
        parameters,
    )
    if mcp_alias_method_id:
        input_config["method_id"] = mcp_alias_method_id


def _normalize_configure_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize configure_subsection arguments to canonical schema.

    Supports a legacy/LLM-produced shape where parameters are placed at:
      data_source_config.parameters
    instead of:
      data_source_config.inputs[i].parameters
    """
    normalized = deepcopy(arguments)
    config = normalized.get("data_source_config")
    if not isinstance(config, dict):
        return normalized

    subsection_id = normalized.get("subsection_id")
    existing_config: dict[str, Any] | None = None
    if isinstance(subsection_id, str) and subsection_id:
        existing_subsection = get_subsection(subsection_id, include_versions=False)
        if isinstance(existing_subsection, dict) and "error" not in existing_subsection:
            candidate_config = existing_subsection.get("data_source_config")
            if isinstance(candidate_config, dict):
                existing_config = candidate_config

    shared_parameters = config.get("parameters")
    inputs = config.get("inputs")
    if isinstance(shared_parameters, dict) and isinstance(inputs, list):
        for input_config in inputs:
            if not isinstance(input_config, dict):
                continue
            existing_parameters = input_config.get("parameters")
            if not isinstance(existing_parameters, dict):
                existing_parameters = {}
            merged_parameters = {**shared_parameters, **existing_parameters}
            if merged_parameters:
                input_config["parameters"] = merged_parameters
        config.pop("parameters", None)

    # Canonicalize source/method aliases from model-generated variants.
    if isinstance(inputs, list):
        data_sources = get_data_sources(active_only=True)
        registry_by_id = {
            source["id"]: source
            for source in data_sources
            if isinstance(source, dict) and isinstance(source.get("id"), str)
        }
        source_id_lookup = {source_id.lower(): source_id for source_id in registry_by_id}
        source_name_lookup = {}
        for source in data_sources:
            if not isinstance(source, dict):
                continue
            source_name = source.get("name")
            source_id = source.get("id")
            if isinstance(source_name, str) and isinstance(source_id, str):
                source_name_lookup[source_name.strip().lower()] = source_id

        for input_config in inputs:
            _normalize_data_input_identifiers(
                input_config,
                registry_by_id,
                source_id_lookup,
                source_name_lookup,
            )

    # Backfill missing per-input parameters from existing subsection config when available.
    if isinstance(inputs, list) and isinstance(existing_config, dict):
        existing_inputs = (
            existing_config.get("inputs")
            if isinstance(existing_config, dict)
            else None
        )
        if isinstance(existing_inputs, list):
            for input_config in inputs:
                if not isinstance(input_config, dict):
                    continue
                input_parameters = input_config.get("parameters")
                if isinstance(input_parameters, dict) and input_parameters:
                    continue

                source_id = input_config.get("source_id")
                method_id = input_config.get("method_id")
                if not isinstance(source_id, str) or not isinstance(method_id, str):
                    continue

                matching_existing = next(
                    (
                        existing_input
                        for existing_input in existing_inputs
                        if (
                            isinstance(existing_input, dict)
                            and existing_input.get("source_id") == source_id
                            and existing_input.get("method_id") == method_id
                            and isinstance(existing_input.get("parameters"), dict)
                        )
                    ),
                    None,
                )
                if matching_existing:
                    input_config["parameters"] = dict(matching_existing["parameters"])

    # Preserve existing visualization settings when a follow-up configure call
    # omits visualization fields for an already-charted subsection.
    if "visualization" not in config and isinstance(existing_config, dict):
        existing_visualization = existing_config.get("visualization")
        if isinstance(existing_visualization, dict):
            config["visualization"] = deepcopy(existing_visualization)

    normalized["data_source_config"] = config
    return normalized


def _score_configure_arguments(arguments: dict[str, Any]) -> int:
    """
    Score configure_subsection argument completeness.

    Higher score indicates a more complete configuration candidate when the
    model emits multiple configure_subsection calls for the same subsection in
    one assistant message.
    """
    score = 0

    if arguments.get("widget_type"):
        score += 1

    config = arguments.get("data_source_config")
    if not isinstance(config, dict):
        return score

    inputs = config.get("inputs")
    if isinstance(inputs, list):
        score += len(inputs) * 10
        for input_config in inputs:
            if not isinstance(input_config, dict):
                continue
            if input_config.get("source_id"):
                score += 2
            if input_config.get("method_id"):
                score += 2
            parameters = input_config.get("parameters")
            if isinstance(parameters, dict):
                score += len([k for k, v in parameters.items() if k and v is not None])

    dependencies = config.get("dependencies")
    if isinstance(dependencies, dict):
        section_ids = dependencies.get("section_ids")
        subsection_ids = dependencies.get("subsection_ids")
        if isinstance(section_ids, list):
            score += len(section_ids)
        if isinstance(subsection_ids, list):
            score += len(subsection_ids)

    # Prefer configure calls that preserve explicit chart metadata.
    visualization = config.get("visualization")
    if isinstance(visualization, dict):
        score += 15
        if visualization.get("chart_type"):
            score += 3
        for key in ("x_key", "y_key", "series_key", "metric_id", "title"):
            if visualization.get(key):
                score += 1

    return score


def _choose_best_configure_calls(
    tool_calls: list[Any],
    section_reference_map: dict[str, str],
    subsection_reference_map: dict[str, str],
) -> dict[int, str]:
    """
    Select the strongest configure_subsection call per subsection.

    Returns:
        Map of tool_call index -> subsection_id for calls that should execute.
    """
    best_by_subsection: dict[str, tuple[int, int]] = {}

    for index, tool_call in enumerate(tool_calls):
        if tool_call.function.name != "configure_subsection":
            continue
        try:
            raw_arguments = json.loads(tool_call.function.arguments)
        except (json.JSONDecodeError, TypeError):
            continue

        arguments = _normalize_tool_references(
            raw_arguments,
            section_reference_map,
            subsection_reference_map,
        )
        arguments = _normalize_configure_arguments(arguments)
        subsection_id = arguments.get("subsection_id")
        if not isinstance(subsection_id, str) or not subsection_id:
            continue

        score = _score_configure_arguments(arguments)
        current = best_by_subsection.get(subsection_id)
        if current is None or score > current[0] or (score == current[0] and index > current[1]):
            best_by_subsection[subsection_id] = (score, index)

    executable_indexes: dict[int, str] = {}
    for subsection_id, (_, index) in best_by_subsection.items():
        executable_indexes[index] = subsection_id
    return executable_indexes


def execute_tool(tool_name: str, arguments: dict) -> Any:
    """
    Execute a tool by name with given arguments.

    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments as dict

    Returns:
        Tool execution result

    Raises:
        ValueError: If tool not found in registry
    """
    if tool_name not in TOOL_REGISTRY:
        raise ValueError(f"Unknown tool: {tool_name}")

    func = TOOL_REGISTRY[tool_name]
    return func(**arguments)


def _build_tool_log_entry(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    result: Any = None,
    error: str | None = None,
    raw_arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a consistent tool-call log entry with optional pre-normalization args."""
    entry: dict[str, Any] = {
        "tool": tool_name,
        "args": arguments,
    }
    if raw_arguments is not None and raw_arguments != arguments:
        entry["raw_args"] = raw_arguments
    if result is not None:
        entry["result"] = result
    if error is not None:
        entry["error"] = error
    return entry


# ============================================================
# Tool Format Conversion
# ============================================================

LIST_UPLOADS_TOOL = {
    "name": "list_uploads",
    "description": """List all uploaded documents for the current template.

Returns metadata about each upload including filename, content type, and extraction status.
Use this to see what documents the user has uploaded that you can reference.""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "template_id": {
                "type": "string",
                "description": "Template UUID to list uploads for"
            }
        },
        "required": ["template_id"]
    }
}


def _get_all_mcp_tools() -> list[dict]:
    """Collect all MCP tool definitions."""
    tools = []

    # Data retrieval tools
    tools.append(TRANSCRIPTS_TOOL)
    tools.append(FINANCIALS_TOOL)
    tools.append(STOCK_PRICES_TOOL)

    # Workspace tools
    for tool_def in TEMPLATE_TOOLS.values():
        tools.append(tool_def)
    for tool_def in SECTION_TOOLS.values():
        tools.append(tool_def)
    for tool_def in SUBSECTION_TOOLS.values():
        tools.append(tool_def)

    # Data sources tool
    tools.append(DATA_SOURCES_TOOL)

    # Upload tools
    tools.append(LIST_UPLOADS_TOOL)
    tools.append(UPLOADS_TOOL)

    return tools


REFERENCE_FIELD_HINTS = {
    "section_id": "Use section refs like `S1` when available; UUIDs are fallback only.",
    "subsection_id": "Use subsection refs like `S1A` when available; UUIDs are fallback only.",
    "section_ids": "Use section refs like `S1` when available; UUIDs are fallback only.",
    "subsection_ids": "Use subsection refs like `S1A` when available; UUIDs are fallback only.",
}


def _append_schema_hint(description: Any, hint: str) -> str:
    """Append guidance text to a schema description without duplicating hints."""
    base = description.strip() if isinstance(description, str) else ""
    if hint in base:
        return base
    if not base:
        return hint
    if base.endswith((".", "!", "?")):
        return f"{base} {hint}"
    return f"{base}. {hint}"


def _inject_reference_guidance(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Add ref-first guidance to ID fields in tool schemas.

    This nudges the model to emit compact refs (S1/S1A) in tool calls, while
    keeping UUIDs supported as a fallback.
    """
    normalized = deepcopy(schema)

    def _visit(node: Any) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                for prop_name, prop_schema in properties.items():
                    if not isinstance(prop_schema, dict):
                        continue
                    hint = REFERENCE_FIELD_HINTS.get(prop_name)
                    if hint:
                        prop_schema["description"] = _append_schema_hint(
                            prop_schema.get("description"),
                            hint,
                        )
                    _visit(prop_schema)

            items = node.get("items")
            if isinstance(items, dict):
                _visit(items)

            for variant_key in ("allOf", "anyOf", "oneOf"):
                variants = node.get(variant_key)
                if isinstance(variants, list):
                    for variant in variants:
                        _visit(variant)

        elif isinstance(node, list):
            for item in node:
                _visit(item)

    _visit(normalized)
    return normalized


def convert_mcp_to_openai_tools(mcp_tools: list[dict]) -> list[dict]:
    """
    Convert MCP tool definitions to OpenAI function calling format.

    MCP format:
    {
        "name": "tool_name",
        "description": "...",
        "inputSchema": {
            "type": "object",
            "properties": {...},
            "required": [...]
        }
    }

    OpenAI format:
    {
        "type": "function",
        "function": {
            "name": "tool_name",
            "description": "...",
            "parameters": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }
    }
    """
    openai_tools = []

    for mcp_tool in mcp_tools:
        openai_tool = {
            "type": "function",
            "function": {
                "name": mcp_tool["name"],
                "description": mcp_tool["description"],
                "parameters": _inject_reference_guidance(mcp_tool["inputSchema"]),
            }
        }
        openai_tools.append(openai_tool)

    return openai_tools


def get_openai_tools() -> list[dict]:
    """Get all tools in OpenAI function format."""
    mcp_tools = _get_all_mcp_tools()
    return convert_mcp_to_openai_tools(mcp_tools)


# ============================================================
# System Prompt Builder
# ============================================================

SYSTEM_PROMPT_TEMPLATE = """You are an AI assistant helping design and generate financial reports for Canadian Big 6 banks.

## Current Template
**Template ID: {template_id}** (use this UUID for template-level tools; use refs like `S1`/`S1A` for section/subsection tool arguments)
Name: {template_name}
Description: {template_description}
Format: {output_format} ({orientation})
Status: {status}
Formatting Profile: {formatting_profile_summary}

## Document Structure
{sections_summary}

## Available Data Sources
- **Transcripts**: Earnings call transcripts (management_discussion, qa sections)
  - Banks: RY, TD, BMO, BNS, CM, NA
  - Periods: FY2024 Q1-Q4, FY2025 Q1
- **Financials**: 25 financial metrics across categories:
  - Profitability: total_revenue, net_income, diluted_eps, roe, roa
  - Capital: cet1_ratio, tier1_ratio, total_capital_ratio, book_value_per_share
  - Efficiency: nim, efficiency_ratio, operating_leverage, net_interest_income
  - Credit: pcl, pcl_ratio, gross_impaired_loans, gil_ratio
  - Balance Sheet: total_assets, total_loans, total_deposits, loan_to_deposit_ratio, common_equity
  - Other: non_interest_revenue, aum, dividend_per_share
- **Stock Prices**: Quarter-end closing prices with QoQ/YoY changes
- **Uploaded Documents**: User-uploaded PDFs, Word docs, and text files
  - Use list_uploads to see available documents
  - Use get_uploaded_document to retrieve document content

{focus_context}

## Your Capabilities
You can help users by:
1. **Retrieve data** from transcripts, financials, and stock prices
2. **Create sections** to organize the report into logical parts
3. **Add subsections** (A, B, C) within sections for different content pieces
4. **Configure subsections** with data sources and widget types
5. **Set instructions** for content generation
6. **Add notes** for collaboration context
7. **Manage template formatting themes** via `update_template.formatting_profile`
8. **Generate and save content** as versioned iterations

## Section Structure
Each section can contain multiple subsections (labeled A, B, C, etc.) that stack vertically.
Each subsection can have:
- An optional title
- Content (markdown formatted)
- Instructions for AI generation
- Notes for collaboration
- Widget type and data source configuration

## Workflow
When generating content:
1. First retrieve relevant data using search_transcripts, search_financials, or search_stock_prices
2. Review the data to understand key insights
3. Craft content based on the user's instructions
4. Save the content using save_subsection_version (include title if appropriate)

## Data Source Configuration Rules
- Always call get_data_sources before configuring if source/method/parameter shape is uncertain.
- Use `by_quarter` methods only for a single bank (`bank_id`).
- Use `compare_banks` methods for multi-bank requests (`bank_ids` array).
- Never pass values like \"all banks\" into `bank_id`; use `bank_ids` with explicit codes instead.
- For transcript management remarks, set `section` to `management_discussion`.
- Always use section/subsection refs in tool arguments (e.g., `S1`, `S1A`) when refs are available in Document Structure.
- UUIDs are internal; only use a UUID when the user explicitly provides one.
- In `configure_subsection`, `subsection_id` must identify a subsection (never a section).
- Put retrieval parameters under `data_source_config.inputs[i].parameters` (not top-level `data_source_config.parameters`).
- `source_id` must match registry IDs (`transcripts`, `financials`, `stock_prices`) and `method_id` must match retrieval method IDs (`by_quarter`, `compare_banks`, `trend` where applicable).
- For chart subsections, use `widget_type='chart'` and set `data_source_config.visualization` when chart settings are requested.
- Call `configure_subsection` once per subsection update; do not repeat identical calls unless parameters changed.

## Important: Selected vs New
- If a subsection is **currently selected** (shown in Current Focus), requests to "update", "modify", "set instructions", or "generate content" apply to THAT subsection
- Requests to "create a new subsection" or "add another subsection" mean calling create_subsection to make a NEW one
- When creating a new subsection, use the section ref in `section_id` from the Current Focus (e.g., `S2`)
- Don't confuse "edit this subsection" with "create a new subsection" - they are different operations

Always confirm with the user before making significant changes to the template structure."""


def _summarize_formatting_profile(formatting_profile: Any) -> str:
    """Create a compact summary of template formatting preferences."""
    if not isinstance(formatting_profile, dict) or not formatting_profile:
        return "Default profile"

    theme_name = formatting_profile.get("theme_name") or formatting_profile.get("theme_id") or "custom"
    font_family = formatting_profile.get("font_family") or "default font"
    title_case = formatting_profile.get("subsection_title_case") or "title"
    accent = formatting_profile.get("accent_color") or "n/a"
    return f"{theme_name} | font: {font_family} | title case: {title_case} | accent: {accent}"


def build_system_prompt(
    template_id: str,
    focus_section_id: str = None,
    focus_subsection_id: str = None,
) -> str:
    """
    Build context-aware system prompt for the agent.

    Args:
        template_id: The template being worked on
        focus_section_id: Optional section focus
        focus_subsection_id: Optional subsection focus

    Returns:
        Formatted system prompt string
    """
    # Get template info
    section_ref_by_id: dict[str, str] = {}
    subsection_ref_by_id: dict[str, str] = {}

    template_data = get_template(template_id)
    if "error" in template_data:
        template_info = {
            "template_id": template_id,
            "template_name": "Unknown",
            "template_description": "Template not found",
            "output_format": "N/A",
            "orientation": "N/A",
            "status": "N/A",
            "formatting_profile_summary": "Default profile",
        }
        sections_summary = "No sections"
    else:
        template = template_data["template"]
        sections = template_data["sections_summary"]["sections"]

        template_info = {
            "template_id": template_id,
            "template_name": template["name"],
            "template_description": template.get("description") or "No description",
            "output_format": template["output_format"],
            "orientation": template.get("orientation", "landscape"),
            "status": template["status"],
            "formatting_profile_summary": _summarize_formatting_profile(
                template.get("formatting_profile")
            ),
        }

        # Build sections summary with section + subsection IDs for tool calls.
        if sections:
            detailed_sections = get_sections(template_id, include_content=False)
            detailed_by_id = {}
            if isinstance(detailed_sections, list):
                detailed_by_id = {
                    section["id"]: section
                    for section in detailed_sections
                    if isinstance(section, dict) and isinstance(section.get("id"), str)
                }

            section_lines = []
            for s in sections:
                subsection_count = s.get("subsection_count")
                if not isinstance(subsection_count, int):
                    subsections = s.get("subsections", [])
                    if (
                        isinstance(subsections, list)
                        and len(subsections) == 1
                        and isinstance(subsections[0], dict)
                        and isinstance(subsections[0].get("count"), int)
                    ):
                        subsection_count = subsections[0]["count"]
                    else:
                        subsection_count = len(subsections) if isinstance(subsections, list) else 0
                section_position = s.get("position")
                section_ref = f"S{section_position}" if isinstance(section_position, int) else "S?"
                section_ref_by_id[s["id"]] = section_ref
                section_lines.append(
                    f"- Section {s['position']}: \"{s['title'] or 'Untitled'}\" "
                    f"(Ref: {section_ref}) - "
                    f"{subsection_count} subsection{'s' if subsection_count != 1 else ''}"
                )

                detailed_section = detailed_by_id.get(s["id"])
                detailed_subsections = (
                    detailed_section.get("subsections")
                    if isinstance(detailed_section, dict)
                    else None
                )
                if isinstance(detailed_subsections, list) and detailed_subsections:
                    sorted_subsections = sorted(
                        (
                            sub
                            for sub in detailed_subsections
                            if isinstance(sub, dict) and isinstance(sub.get("id"), str)
                        ),
                        key=lambda sub: sub.get("position", 0),
                    )
                    for sub in sorted_subsections:
                        position = sub.get("position", 1)
                        label = chr(64 + position) if isinstance(position, int) and 1 <= position <= 26 else str(position)
                        sub_title = sub.get("title") or "Untitled"
                        subsection_ref = f"{section_ref}{label}" if isinstance(section_position, int) else str(label)
                        subsection_ref_by_id[sub["id"]] = subsection_ref
                        section_lines.append(
                            f"  - Subsection {label}: \"{sub_title}\" "
                            f"(Ref: {subsection_ref})"
                        )
            sections_summary = "\n".join(section_lines)
        else:
            sections_summary = "No sections yet. Help the user create the first section."

    # Build focus context
    focus_context = ""
    if focus_section_id:
        current_section_ref = section_ref_by_id.get(focus_section_id, focus_section_id)
        focus_context = f"\n## Current Focus\nWorking on Section: {current_section_ref}"

        # Get all subsections in this section for context
        section_data = get_sections(template_id, include_content=False)
        focused_section = next((s for s in section_data if s['id'] == focus_section_id), None)
        if focused_section:
            focus_context += f"\nSection Title: {focused_section.get('title', 'Untitled')}"
            subsections = focused_section.get('subsections', [])
            if subsections:
                focus_context += f"\nSubsections in this section:"
                for sub in subsections:
                    pos = sub.get('position', 1)
                    label = chr(64 + pos)  # 1 -> A, 2 -> B, etc.
                    sub_title = sub.get('title') or '(no title)'
                    section_position = focused_section.get("position")
                    subsection_ref = (
                        f"S{section_position}{label}"
                        if isinstance(section_position, int)
                        else label
                    )
                    focus_context += f"\n  - {label}: {sub_title} (Ref: {subsection_ref})"
                    if isinstance(sub.get("id"), str):
                        subsection_ref_by_id[sub["id"]] = subsection_ref

        if focus_subsection_id:
            selected_subsection_ref = subsection_ref_by_id.get(focus_subsection_id, focus_subsection_id)
            focus_context += f"\n\n**Currently Selected Subsection: {selected_subsection_ref}**"
            # Get subsection details
            subsection = get_subsection(focus_subsection_id, include_versions=False)
            if "error" not in subsection:
                position = subsection.get('position', 1)
                label = chr(64 + position)  # 1 -> A, 2 -> B, etc.
                focus_context += f"\nSubsection: {label}"
                if subsection.get("title"):
                    focus_context += f" - {subsection['title']}"
                if subsection.get("instructions"):
                    focus_context += f"\nCurrent Instructions: {subsection['instructions'][:200]}..."
                if subsection.get("notes"):
                    focus_context += f"\nNotes: {subsection['notes'][:200]}..."

    return SYSTEM_PROMPT_TEMPLATE.format(
        sections_summary=sections_summary,
        focus_context=focus_context,
        **template_info,
    )


# ============================================================
# Chat Completion Handler
# ============================================================

async def chat_with_agent(
    template_id: str,
    user_message: str,
    focus_section_id: str = None,
    focus_subsection_id: str = None,
) -> dict:
    """
    Main entry point for agent chat.

    Args:
        template_id: Template being worked on
        user_message: User's message
        focus_section_id: Optional section focus
        focus_subsection_id: Optional subsection focus

    Returns:
        {
            "response": str,
            "tool_calls": list[{tool, args, result}],
            "conversation_id": str,
        }
    """
    # Get or create conversation
    conversation = get_or_create_conversation(template_id)
    conversation_id = conversation["id"]

    # Save user message
    add_message(
        conversation_id=conversation_id,
        role="user",
        content=user_message,
        section_id=focus_section_id,
        subsection_id=focus_subsection_id,
    )

    # Build system prompt
    system_prompt = build_system_prompt(
        template_id=template_id,
        focus_section_id=focus_section_id,
        focus_subsection_id=focus_subsection_id,
    )

    # Get conversation history for context
    history = get_messages_for_openai(conversation_id, limit=20)

    # Build messages for OpenAI
    messages = [
        {"role": "system", "content": system_prompt},
    ]
    messages.extend(history)

    # Get tools in OpenAI format
    openai_tools = get_openai_tools()
    section_reference_map, subsection_reference_map = _build_reference_maps(template_id)
    section_id_to_ref, subsection_id_to_ref = _build_primary_id_to_ref_maps(
        section_reference_map,
        subsection_reference_map,
    )

    # Tool calling loop
    tool_calls_log = []
    seen_configure_signatures: set[str] = set()
    configure_failure_counts: dict[str, int] = {}
    iteration = 0

    while iteration < MAX_TOOL_ITERATIONS:
        iteration += 1

        # Call OpenAI
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=openai_tools,
            tool_choice="auto",
        )

        assistant_message = response.choices[0].message

        # If no tool calls, we're done
        if not assistant_message.tool_calls:
            final_response = assistant_message.content or ""

            # Save assistant response
            add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=final_response,
                section_id=focus_section_id,
                subsection_id=focus_subsection_id,
            )

            return {
                "response": final_response,
                "tool_calls": tool_calls_log,
                "conversation_id": conversation_id,
            }

        # Add assistant message to conversation (with tool calls)
        messages.append({
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in assistant_message.tool_calls
            ]
        })

        best_configure_call_indexes = _choose_best_configure_calls(
            assistant_message.tool_calls,
            section_reference_map,
            subsection_reference_map,
        )
        best_configure_subsection_ids = set(best_configure_call_indexes.values())

        # Execute each tool call
        for index, tool_call in enumerate(assistant_message.tool_calls):
            tool_name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as e:
                arguments = {}
                result = {"error": f"Invalid JSON arguments: {e}"}
                tool_calls_log.append({
                    "tool": tool_name,
                    "args": {},
                    "error": str(e),
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })
                continue
            raw_arguments = deepcopy(arguments)

            arguments = _normalize_tool_references(
                arguments,
                section_reference_map,
                subsection_reference_map,
            )

            if tool_name == "configure_subsection":
                arguments = _normalize_configure_arguments(arguments)
                subsection_id = arguments.get("subsection_id")
                if isinstance(subsection_id, str) and subsection_id:
                    failure_count = configure_failure_counts.get(subsection_id, 0)
                    if failure_count >= 3:
                        result = {
                            "status": "skipped_after_retries",
                            "message": "Skipped configure_subsection because this subsection already had multiple failed configuration attempts in this response cycle.",
                        }
                        tool_calls_log.append(
                            _build_tool_log_entry(
                                tool_name,
                                arguments,
                                result=result,
                                raw_arguments=raw_arguments,
                            )
                        )
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result, default=str),
                        })
                        continue

                if (
                    isinstance(subsection_id, str)
                    and subsection_id
                    and subsection_id in best_configure_subsection_ids
                    and index not in best_configure_call_indexes
                ):
                    result = {
                        "status": "skipped_superseded",
                        "message": "Skipped configure_subsection call because a more complete configuration for this subsection exists in the same assistant response.",
                    }
                    tool_calls_log.append(
                        _build_tool_log_entry(
                            tool_name,
                            arguments,
                            result=result,
                            raw_arguments=raw_arguments,
                        )
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, default=str),
                    })
                    continue

            configure_signature = None
            if tool_name == "configure_subsection":
                configure_signature = _build_tool_signature(tool_name, arguments)
                if configure_signature in seen_configure_signatures:
                    result = {
                        "status": "skipped_duplicate",
                        "message": "Skipped duplicate configure_subsection call with identical arguments in the same response cycle.",
                    }
                    tool_calls_log.append(
                        _build_tool_log_entry(
                            tool_name,
                            arguments,
                            result=result,
                            raw_arguments=raw_arguments,
                        )
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, default=str),
                    })
                    continue

            try:
                result = execute_tool(tool_name, arguments)
                tool_calls_log.append(
                    _build_tool_log_entry(
                        tool_name,
                        arguments,
                        result=result,
                        raw_arguments=raw_arguments,
                    )
                )
                if tool_name == "configure_subsection":
                    subsection_id = arguments.get("subsection_id")
                    if isinstance(subsection_id, str) and subsection_id:
                        if isinstance(result, dict) and result.get("error"):
                            configure_failure_counts[subsection_id] = (
                                configure_failure_counts.get(subsection_id, 0) + 1
                            )
                        else:
                            configure_failure_counts[subsection_id] = 0
                if configure_signature is not None:
                    seen_configure_signatures.add(configure_signature)
                if (
                    tool_name in STRUCTURE_MUTATION_TOOLS
                    and isinstance(result, dict)
                    and "error" not in result
                ):
                    section_reference_map, subsection_reference_map = _build_reference_maps(
                        template_id
                    )
                    section_id_to_ref, subsection_id_to_ref = _build_primary_id_to_ref_maps(
                        section_reference_map,
                        subsection_reference_map,
                    )
            except Exception as e:
                result = {"error": str(e)}
                tool_calls_log.append(
                    _build_tool_log_entry(
                        tool_name,
                        arguments,
                        error=str(e),
                        raw_arguments=raw_arguments,
                    )
                )

            # Add tool result to messages
            model_result = _sanitize_tool_result_for_model(
                result,
                section_id_to_ref,
                subsection_id_to_ref,
            )
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(model_result, default=str),
            })

    # Max iterations reached
    final_response = "I've reached the maximum number of operations. Please continue with a new message or refine your request."

    add_message(
        conversation_id=conversation_id,
        role="assistant",
        content=final_response,
        section_id=focus_section_id,
        subsection_id=focus_subsection_id,
    )

    return {
        "response": final_response,
        "tool_calls": tool_calls_log,
        "conversation_id": conversation_id,
    }
