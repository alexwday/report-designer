"""
Generation pipeline for batch content generation.

Handles:
- Sequential generation with context accumulation
- Progress tracking for UI polling
- Cross-section coherence
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from ..workspace import (
    get_template,
    get_sections,
    get_subsection,
    save_subsection_version,
    get_template_generation_preset,
    save_template_generation_preset,
)
from ..workspace.data_sources import (
    collect_variable_bindings,
    collect_period_bindings,
    get_data_source_method_details,
    PERIOD_ANCHOR_YEAR_KEY,
    PERIOD_ANCHOR_QUARTER_KEY,
    VALID_FISCAL_QUARTERS,
    DEPENDENCY_SECTION_IDS_KEY,
    DEPENDENCY_SUBSECTION_IDS_KEY,
    get_section_period_anchor_year_key,
    get_section_period_anchor_quarter_key,
    extract_data_input_configs,
    extract_context_dependencies,
    extract_visualization_config,
    resolve_data_source_config,
)
from ..workspace.sections import get_section_by_id
from ..retrievers.transcripts import search_transcripts
from ..retrievers.financials import search_financials
from ..retrievers.stock_prices import search_stock_prices
from ..config.settings import get_settings
from ..infra.llm import get_openai_client


# Configuration
OPENAI_MODEL = get_settings().OPENAI_MODEL
client = get_openai_client()


class GenerationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


def position_to_label(position: int) -> str:
    """Convert position number to letter label (1 -> A, 2 -> B, etc.)."""
    if position < 1:
        return "?"
    return chr(64 + position)


@dataclass
class SubsectionProgress:
    subsection_id: str
    title: Optional[str]
    position: int
    section_title: str
    widget_type: Optional[str] = None
    resolved_data_source_config: Optional[dict] = None
    dependency_subsection_ids: list[str] = field(default_factory=list)
    status: GenerationStatus = GenerationStatus.PENDING
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class GenerationJob:
    job_id: str
    template_id: str
    status: GenerationStatus = GenerationStatus.PENDING
    subsections: list[SubsectionProgress] = field(default_factory=list)
    current_index: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    generated_context: list[dict] = field(default_factory=list)


# In-memory job store (in production, use Redis or database)
_jobs: dict[str, GenerationJob] = {}


def _validate_data_source_config(
    subsection: dict,
    run_inputs: dict | None = None,
    section_id: str | None = None,
) -> tuple[Optional[str], Optional[dict]]:
    """
    Validate and resolve subsection data source config against schema.

    Returns:
        (error_message_or_none, resolved_config_or_none)
    """
    resolution = resolve_data_source_config(
        subsection.get("data_source_config"),
        run_inputs=run_inputs,
        section_id=section_id or subsection.get("section_id"),
    )
    if resolution["valid"]:
        return None, resolution["resolved_config"]
    error = "; ".join(resolution["errors"]) if resolution["errors"] else "Invalid data source configuration"
    return error, None


def _build_validation_error(subsection: dict, section_title: str, reason: str) -> dict:
    """Build a consistent validation error payload for generation readiness checks."""
    return {
        "subsection_id": subsection.get("id"),
        "subsection_title": subsection.get("title"),
        "subsection_position": subsection.get("position"),
        "section_title": section_title,
        "reason": reason,
    }


def _build_generation_context_entry(
    section_title: str,
    subsection_title: str,
    content: str,
    subsection_id: str | None = None,
) -> dict:
    """Format generated subsection output for context accumulation."""
    entry = {
        "section": section_title,
        "subsection": subsection_title,
        "content_summary": content[:500] if len(content) > 500 else content,
    }
    if subsection_id:
        entry["subsection_id"] = subsection_id
    return entry


def _build_template_structure_maps(
    sections: list[dict],
) -> tuple[dict[str, list[str]], dict[str, tuple[int, int]]]:
    """
    Build helper maps for subsection dependency resolution and deterministic ordering.

    Returns:
        (
            section_id -> ordered subsection ids,
            subsection_id -> (section_position, subsection_position),
        )
    """
    section_to_subsections: dict[str, list[str]] = {}
    subsection_order_map: dict[str, tuple[int, int]] = {}

    for section in sections:
        section_id = section.get("id")
        if not section_id:
            continue
        section_position = int(section.get("position") or 0)
        subsection_ids: list[str] = []

        ordered_subsections = sorted(
            section.get("subsections", []),
            key=lambda sub: sub.get("position", 1),
        )
        for subsection in ordered_subsections:
            subsection_id = subsection.get("id")
            if not subsection_id:
                continue
            subsection_ids.append(subsection_id)
            subsection_order_map[subsection_id] = (
                section_position,
                int(subsection.get("position") or 0),
            )

        section_to_subsections[section_id] = subsection_ids

    return section_to_subsections, subsection_order_map


def _resolve_dependency_subsection_ids(
    resolved_data_source_config: dict | None,
    section_to_subsections: dict[str, list[str]],
    current_subsection_id: str | None = None,
) -> list[str]:
    """Expand subsection+section dependency references into ordered subsection ids."""
    dependencies = extract_context_dependencies(resolved_data_source_config)

    dependency_ids: list[str] = []
    seen: set[str] = set()

    for section_id in dependencies[DEPENDENCY_SECTION_IDS_KEY]:
        for subsection_id in section_to_subsections.get(section_id, []):
            if current_subsection_id and subsection_id == current_subsection_id:
                continue
            if subsection_id in seen:
                continue
            seen.add(subsection_id)
            dependency_ids.append(subsection_id)

    for subsection_id in dependencies[DEPENDENCY_SUBSECTION_IDS_KEY]:
        if current_subsection_id and subsection_id == current_subsection_id:
            continue
        if subsection_id in seen:
            continue
        seen.add(subsection_id)
        dependency_ids.append(subsection_id)

    return dependency_ids


def _topological_order_subsection_ids(
    subsection_ids: list[str],
    dependency_map: dict[str, list[str]],
    subsection_order_map: dict[str, tuple[int, int]],
) -> tuple[list[str], Optional[str]]:
    """Return dependency-respecting subsection order, or an error if cycle detected."""
    if not subsection_ids:
        return [], None

    node_set = set(subsection_ids)
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in subsection_ids}
    indegree: dict[str, int] = {node_id: 0 for node_id in subsection_ids}

    for node_id in subsection_ids:
        for dependency_id in dependency_map.get(node_id, []):
            if dependency_id not in node_set:
                continue
            if dependency_id == node_id:
                return [], f"Circular subsection dependency detected on subsection '{node_id}'"
            if node_id in adjacency[dependency_id]:
                continue
            adjacency[dependency_id].add(node_id)
            indegree[node_id] += 1

    def sort_key(subsection_id: str) -> tuple[int, int, str]:
        section_position, subsection_position = subsection_order_map.get(
            subsection_id,
            (10_000_000, 10_000_000),
        )
        return section_position, subsection_position, subsection_id

    ready = sorted(
        [node_id for node_id in subsection_ids if indegree[node_id] == 0],
        key=sort_key,
    )
    ordered: list[str] = []

    while ready:
        current_id = ready.pop(0)
        ordered.append(current_id)

        for dependent_id in sorted(adjacency[current_id], key=sort_key):
            indegree[dependent_id] -= 1
            if indegree[dependent_id] == 0:
                ready.append(dependent_id)
        ready.sort(key=sort_key)

    if len(ordered) != len(subsection_ids):
        cycle_nodes = [node_id for node_id in subsection_ids if indegree[node_id] > 0]
        return [], f"Circular subsection dependencies detected: {', '.join(cycle_nodes)}"

    return ordered, None


def get_generation_requirements(template_id: str) -> dict:
    """
    Inspect template subsections and return run inputs required for generation.

    This scans eligible subsections (instruction-driven text subsections and
    chart widgets), validates configured data inputs, and extracts variable
    bindings from input parameters.
    """
    preset = get_template_generation_preset(template_id)
    saved_run_inputs = preset.get("run_inputs") if isinstance(preset, dict) else {}
    if not isinstance(saved_run_inputs, dict):
        saved_run_inputs = {}

    sections = get_sections(template_id, include_content=True)
    if not sections:
        return {
            "ready": False,
            "required_inputs": [],
            "blocking_errors": [
                {
                    "subsection_id": "",
                    "subsection_title": None,
                    "subsection_position": 0,
                    "section_title": "Template",
                    "reason": "No sections found in template",
                }
            ],
            "subsections_considered": 0,
            "saved_run_inputs": saved_run_inputs,
        }

    required_inputs: dict[str, dict] = {}
    blocking_errors: list[dict] = []
    subsections_considered = 0

    def add_required_input(
        key: str,
        label: str,
        input_type: str,
        options: list[str] | None,
        *,
        subsection: dict,
        section_title: str,
        parameter_key: str,
    ) -> None:
        if key not in required_inputs:
            required_inputs[key] = {
                "key": key,
                "label": label,
                "type": input_type,
                "options": options,
                "used_by": [],
            }
        required_inputs[key]["used_by"].append({
            "subsection_id": subsection.get("id"),
            "section_title": section_title,
            "subsection_title": subsection.get("title"),
            "parameter_key": parameter_key,
        })

    for section in sections:
        section_title = section.get("title") or f"Section {section.get('position', '?')}"
        for subsection in section.get("subsections", []):
            is_chart_subsection = subsection.get("widget_type") == "chart"
            if not subsection.get("instructions") and not is_chart_subsection:
                continue

            subsections_considered += 1
            resolution_error, _resolved = _validate_data_source_config(
                subsection,
                run_inputs={},
                section_id=section.get("id"),
            )
            if resolution_error and not resolution_error.startswith("Missing run input"):
                blocking_errors.append(
                    _build_validation_error(
                        subsection=subsection,
                        section_title=section_title,
                        reason=resolution_error,
                    )
                )
                continue

            config = _resolved if isinstance(_resolved, dict) else (subsection.get("data_source_config") or {})
            input_configs = extract_data_input_configs(config)
            if not input_configs:
                # Already captured above as blocking error.
                continue

            input_lookup_failed = False
            for input_config in input_configs:
                source_id = input_config.get("source_id")
                method_id = input_config.get("method_id")
                if not source_id or not method_id:
                    continue

                method_lookup = get_data_source_method_details(source_id, method_id)
                if "error" in method_lookup:
                    blocking_errors.append(
                        _build_validation_error(
                            subsection=subsection,
                            section_title=section_title,
                            reason=method_lookup["error"],
                        )
                    )
                    input_lookup_failed = True
                    break

                method = method_lookup["method"]
                parameter_defs = method.get("parameters") or []
                parameters = input_config.get("parameters") or {}
                if not isinstance(parameters, dict):
                    continue

                for param_def in parameter_defs:
                    param_key = param_def.get("key") or param_def.get("name")
                    if not param_key:
                        continue
                    if param_key not in parameters:
                        continue

                    variable_names = collect_variable_bindings(parameters[param_key])
                    for variable_name in variable_names:
                        add_required_input(
                            variable_name,
                            param_def.get("prompt") or param_def.get("description") or variable_name,
                            (param_def.get("type") or "string").lower(),
                            param_def.get("options") or param_def.get("enum"),
                            subsection=subsection,
                            section_title=section_title,
                            parameter_key=param_key,
                        )

                    period_bindings = collect_period_bindings(parameters[param_key])
                    if period_bindings:
                        section_id = section.get("id")
                        year_input_key = (
                            get_section_period_anchor_year_key(section_id)
                            if section_id else PERIOD_ANCHOR_YEAR_KEY
                        )
                        quarter_input_key = (
                            get_section_period_anchor_quarter_key(section_id)
                            if section_id else PERIOD_ANCHOR_QUARTER_KEY
                        )
                        add_required_input(
                            year_input_key,
                            f"{section_title}: Base fiscal year",
                            "integer",
                            None,
                            subsection=subsection,
                            section_title=section_title,
                            parameter_key=param_key,
                        )
                        add_required_input(
                            quarter_input_key,
                            f"{section_title}: Base fiscal quarter",
                            "enum",
                            list(VALID_FISCAL_QUARTERS),
                            subsection=subsection,
                            section_title=section_title,
                            parameter_key=param_key,
                        )
            if input_lookup_failed:
                continue

    required_inputs_list = sorted(required_inputs.values(), key=lambda item: item["key"])
    if subsections_considered == 0:
        return {
            "ready": False,
            "required_inputs": [],
            "blocking_errors": [
                {
                    "subsection_id": "",
                    "subsection_title": None,
                    "subsection_position": 0,
                    "section_title": "Template",
                    "reason": "No eligible subsections found for generation",
                }
            ],
            "subsections_considered": 0,
            "saved_run_inputs": saved_run_inputs,
        }

    return {
        "ready": len(blocking_errors) == 0 and len(required_inputs_list) == 0,
        "required_inputs": required_inputs_list,
        "blocking_errors": blocking_errors,
        "subsections_considered": subsections_considered,
        "saved_run_inputs": saved_run_inputs,
    }


async def generate_subsection(subsection_id: str) -> dict:
    """
    Generate content for a single subsection.

    Strictly requires:
    - instructions to be set for non-chart widgets
    - data_source_config.inputs to contain at least one valid data input
    """
    subsection = get_subsection(subsection_id, include_versions=False)
    if "error" in subsection:
        return {"error": subsection["error"]}

    instructions = subsection.get("instructions")
    is_chart_subsection = subsection.get("widget_type") == "chart"
    if not instructions and not is_chart_subsection:
        return {"error": "Subsection has no instructions. Add instructions before generating content."}

    preset = get_template_generation_preset(subsection["template_id"])
    run_inputs = preset.get("run_inputs") if isinstance(preset, dict) else {}
    if not isinstance(run_inputs, dict):
        run_inputs = {}

    config_error, resolved_config = _validate_data_source_config(
        subsection,
        run_inputs=run_inputs,
        section_id=subsection.get("section_id"),
    )
    if config_error:
        return {
            "error": "Generation blocked: subsection is missing required data source configuration.",
            "validation_errors": [
                _build_validation_error(
                    subsection=subsection,
                    section_title=subsection.get("section_title") or "Unknown section",
                    reason=config_error,
                )
            ],
        }

    template_data = get_template(subsection["template_id"])
    template = template_data.get("template", {})
    template_name = template.get("name", "Report")
    formatting_profile = template.get("formatting_profile")
    section_title = subsection.get("section_title") or "Section"
    label = position_to_label(subsection.get("position", 1))
    sections = get_sections(subsection["template_id"], include_content=True)
    section_to_subsections, _subsection_order_map = _build_template_structure_maps(sections)
    dependency_subsection_ids = _resolve_dependency_subsection_ids(
        resolved_config,
        section_to_subsections=section_to_subsections,
        current_subsection_id=subsection_id,
    )
    dependency_context = _build_dependency_context_from_ids(
        dependency_subsection_ids=dependency_subsection_ids,
        generated_context_by_subsection_id={},
        cached_subsection_context={},
    )

    content_type = "markdown"
    if subsection.get("widget_type") == "chart":
        content, generated_title = await _generate_chart_subsection_content(
            section_title=section_title,
            subsection_title=subsection.get("title"),
            resolved_data_source_config=resolved_config,
        )
        content_type = "json"
    else:
        content, generated_title = await _generate_subsection_content(
            template_name=template_name,
            section_title=section_title,
            subsection_label=label,
            subsection_title=subsection.get("title"),
            instructions=instructions,
            notes=subsection.get("notes"),
            prior_context=dependency_context,
            resolved_data_source_config=resolved_config,
            formatting_profile=formatting_profile,
        )

    save_result = save_subsection_version(
        subsection_id=subsection_id,
        content=content,
        content_type=content_type,
        generated_by="agent",
        title=generated_title if not subsection.get("title") else None,
        generation_context={
            "single_subsection_generate": True,
            "resolved_data_source_config": resolved_config,
            "dependency_subsection_ids": dependency_subsection_ids,
        },
    )
    if "error" in save_result:
        return save_result

    return {
        "generated": True,
        "subsection_id": subsection_id,
        "version_id": save_result["version_id"],
        "version_number": save_result["version_number"],
    }


async def generate_section(section_id: str) -> dict:
    """
    Generate all eligible subsections in a section.

    Strictly requires each target subsection to have:
    - instructions (for non-chart widgets)
    - data_source_config.inputs with at least one valid input
    """
    section = get_section_by_id(section_id)
    if "error" in section:
        return {"error": section["error"]}

    section_title = section.get("title") or f"Section {section.get('position', '?')}"
    template_id = section.get("template_id")
    if not template_id:
        return {"error": f"Section is missing template_id: {section_id}"}

    preset = get_template_generation_preset(template_id)
    run_inputs = preset.get("run_inputs") if isinstance(preset, dict) else {}
    if not isinstance(run_inputs, dict):
        run_inputs = {}

    template_sections = get_sections(template_id, include_content=True)
    section_to_subsections, subsection_order_map = _build_template_structure_maps(template_sections)

    target_subsections: list[dict] = []
    validation_errors: list[dict] = []

    for subsection_stub in section.get("subsections", []):
        subsection = get_subsection(subsection_stub["id"], include_versions=False)
        if "error" in subsection:
            validation_errors.append(
                _build_validation_error(
                    subsection=subsection_stub,
                    section_title=section_title,
                    reason=subsection["error"],
                )
            )
            continue

        is_chart_subsection = subsection.get("widget_type") == "chart"
        if not subsection.get("instructions") and not is_chart_subsection:
            continue

        config_error, resolved_config = _validate_data_source_config(
            subsection,
            run_inputs=run_inputs,
            section_id=section_id,
        )
        if config_error:
            validation_errors.append(
                _build_validation_error(
                    subsection=subsection,
                    section_title=section_title,
                    reason=config_error,
                )
            )
            continue

        subsection["resolved_data_source_config"] = resolved_config
        subsection["dependency_subsection_ids"] = _resolve_dependency_subsection_ids(
            resolved_config,
            section_to_subsections=section_to_subsections,
            current_subsection_id=subsection.get("id"),
        )
        target_subsections.append(subsection)

    if validation_errors:
        return {
            "error": "Generation blocked: one or more subsections are missing required data source configuration.",
            "validation_errors": validation_errors,
        }

    if not target_subsections:
        return {"error": "No eligible subsections found in this section"}

    subsection_ids = [subsection["id"] for subsection in target_subsections]
    dependency_map = {
        subsection["id"]: subsection.get("dependency_subsection_ids", [])
        for subsection in target_subsections
    }
    ordered_subsection_ids, dependency_error = _topological_order_subsection_ids(
        subsection_ids=subsection_ids,
        dependency_map=dependency_map,
        subsection_order_map=subsection_order_map,
    )
    if dependency_error:
        return {"error": dependency_error}

    subsections_by_id = {subsection["id"]: subsection for subsection in target_subsections}
    ordered_target_subsections = [subsections_by_id[subsection_id] for subsection_id in ordered_subsection_ids]

    template_data = get_template(template_id)
    template = template_data.get("template", {})
    template_name = template.get("name", "Report")
    formatting_profile = template.get("formatting_profile")

    generated_context: list[dict] = []
    generated_context_by_subsection_id: dict[str, dict] = {}
    cached_subsection_context: dict[str, Optional[dict]] = {}
    generated_subsections: list[dict] = []
    for index, subsection in enumerate(ordered_target_subsections):
        dependency_context = _build_dependency_context_from_ids(
            dependency_subsection_ids=subsection.get("dependency_subsection_ids", []),
            generated_context_by_subsection_id=generated_context_by_subsection_id,
            cached_subsection_context=cached_subsection_context,
        )
        prior_context = dependency_context or _build_prior_context(generated_context)
        label = position_to_label(subsection.get("position", 1))

        content_type = "markdown"
        if subsection.get("widget_type") == "chart":
            content, generated_title = await _generate_chart_subsection_content(
                section_title=section_title,
                subsection_title=subsection.get("title"),
                resolved_data_source_config=subsection.get("resolved_data_source_config"),
            )
            content_type = "json"
        else:
            content, generated_title = await _generate_subsection_content(
                template_name=template_name,
                section_title=section_title,
                subsection_label=label,
                subsection_title=subsection.get("title"),
                instructions=subsection.get("instructions", ""),
                notes=subsection.get("notes"),
                prior_context=prior_context,
                resolved_data_source_config=subsection.get("resolved_data_source_config"),
                formatting_profile=formatting_profile,
            )

        save_result = save_subsection_version(
            subsection_id=subsection["id"],
            content=content,
            content_type=content_type,
            generated_by="agent",
            title=generated_title if not subsection.get("title") else None,
            generation_context={
                "section_generate": True,
                "generation_index": index,
                "resolved_data_source_config": subsection.get("resolved_data_source_config"),
                "dependency_subsection_ids": subsection.get("dependency_subsection_ids", []),
            },
        )
        if "error" in save_result:
            return save_result

        display_title = subsection.get("title") or generated_title or f"Subsection {label}"
        context_summary = content
        if content_type == "json":
            try:
                parsed_payload = json.loads(content)
                if isinstance(parsed_payload, dict):
                    context_summary = _summarize_chart_payload(parsed_payload)
            except (TypeError, ValueError):
                context_summary = content
        context_entry = _build_generation_context_entry(
            section_title,
            display_title,
            context_summary,
            subsection_id=subsection["id"],
        )
        generated_context.append(context_entry)
        generated_context_by_subsection_id[subsection["id"]] = context_entry
        generated_subsections.append(
            {
                "subsection_id": subsection["id"],
                "version_id": save_result["version_id"],
                "version_number": save_result["version_number"],
            }
        )

    return {
        "generated": True,
        "section_id": section_id,
        "generated_count": len(generated_subsections),
        "generated_subsections": generated_subsections,
    }


def get_generation_status(job_id: str) -> Optional[dict]:
    """Get the current status of a generation job."""
    job = _jobs.get(job_id)
    if not job:
        return None

    return {
        "job_id": job.job_id,
        "template_id": job.template_id,
        "status": job.status.value,
        "current_index": job.current_index,
        "total_subsections": len(job.subsections),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error": job.error,
        "subsections": [
            {
                "subsection_id": s.subsection_id,
                "title": s.title,
                "position": s.position,
                "section_title": s.section_title,
                "widget_type": s.widget_type,
                "status": s.status.value,
                "error": s.error,
            }
            for s in job.subsections
        ],
    }


async def start_generation(template_id: str, run_inputs: dict | None = None) -> dict:
    """
    Start batch generation for a template.

    Returns job_id for status polling.
    """
    # Create job
    job_id = str(uuid.uuid4())
    job = GenerationJob(
        job_id=job_id,
        template_id=template_id,
        started_at=datetime.utcnow(),
    )

    # Get all sections with content
    sections = get_sections(template_id, include_content=True)
    if not sections:
        return {"error": "No sections found in template"}

    preset = get_template_generation_preset(template_id)
    preset_inputs = preset.get("run_inputs") if isinstance(preset, dict) else {}
    if not isinstance(preset_inputs, dict):
        preset_inputs = {}

    provided_inputs = run_inputs if isinstance(run_inputs, dict) else {}
    run_inputs = {**preset_inputs, **provided_inputs}
    section_to_subsections, subsection_order_map = _build_template_structure_maps(sections)

    # Build list of eligible subsections and validate readiness
    validation_errors = []
    for section in sections:
        section_title = section.get("title") or f"Section {section.get('position', '?')}"
        for sub in section.get("subsections", []):
            is_chart_subsection = sub.get("widget_type") == "chart"
            if sub.get("instructions") or is_chart_subsection:
                config_error, resolved_config = _validate_data_source_config(
                    sub,
                    run_inputs=run_inputs,
                    section_id=section.get("id"),
                )
                if config_error:
                    validation_errors.append(
                        _build_validation_error(
                            subsection=sub,
                            section_title=section_title,
                            reason=config_error,
                        )
                    )
                    continue

                dependency_subsection_ids = _resolve_dependency_subsection_ids(
                    resolved_config,
                    section_to_subsections=section_to_subsections,
                    current_subsection_id=sub.get("id"),
                )

                job.subsections.append(SubsectionProgress(
                    subsection_id=sub["id"],
                    title=sub.get("title"),
                    position=sub.get("position", 1),
                    section_title=section_title,
                    widget_type=sub.get("widget_type"),
                    resolved_data_source_config=resolved_config,
                    dependency_subsection_ids=dependency_subsection_ids,
                ))

    if validation_errors:
        return {
            "error": "Generation blocked: one or more eligible subsections are missing data source configuration.",
            "validation_errors": validation_errors,
        }

    if not job.subsections:
        return {"error": "No eligible subsections found"}

    subsection_ids = [progress.subsection_id for progress in job.subsections]
    dependency_map = {
        progress.subsection_id: progress.dependency_subsection_ids
        for progress in job.subsections
    }
    ordered_subsection_ids, dependency_error = _topological_order_subsection_ids(
        subsection_ids=subsection_ids,
        dependency_map=dependency_map,
        subsection_order_map=subsection_order_map,
    )
    if dependency_error:
        return {"error": dependency_error}

    progress_by_id = {progress.subsection_id: progress for progress in job.subsections}
    job.subsections = [progress_by_id[subsection_id] for subsection_id in ordered_subsection_ids]

    # Persist the latest initialization values for future runs.
    try:
        save_template_generation_preset(template_id, run_inputs)
    except Exception:
        # Preset persistence should not block generation.
        pass

    _jobs[job_id] = job

    # Start generation in background
    asyncio.create_task(_run_generation(job))

    return {
        "job_id": job_id,
        "total_subsections": len(job.subsections),
    }


async def _run_generation(job: GenerationJob):
    """Execute the generation pipeline."""
    job.status = GenerationStatus.IN_PROGRESS

    try:
        # Get template info for context
        template_data = get_template(job.template_id)
        template = template_data.get("template", {})
        template_name = template.get("name", "Report")
        formatting_profile = template.get("formatting_profile")
        generated_context_by_subsection_id: dict[str, dict] = {}
        cached_subsection_context: dict[str, Optional[dict]] = {}

        # Generate each subsection sequentially
        for i, progress in enumerate(job.subsections):
            job.current_index = i
            progress.status = GenerationStatus.IN_PROGRESS
            progress.started_at = datetime.utcnow()

            try:
                # Get full subsection details
                subsection = get_subsection(progress.subsection_id, include_versions=False)
                if "error" in subsection:
                    raise ValueError(subsection["error"])

                dependency_context = _build_dependency_context_from_ids(
                    dependency_subsection_ids=progress.dependency_subsection_ids,
                    generated_context_by_subsection_id=generated_context_by_subsection_id,
                    cached_subsection_context=cached_subsection_context,
                )
                prior_context = dependency_context or _build_prior_context(job.generated_context)

                # Generate content
                label = position_to_label(progress.position)
                content_type = "markdown"
                if progress.widget_type == "chart":
                    content, generated_title = await _generate_chart_subsection_content(
                        section_title=progress.section_title,
                        subsection_title=progress.title,
                        resolved_data_source_config=progress.resolved_data_source_config,
                    )
                    content_type = "json"
                else:
                    content, generated_title = await _generate_subsection_content(
                        template_name=template_name,
                        section_title=progress.section_title,
                        subsection_label=label,
                        subsection_title=progress.title,
                        instructions=subsection.get("instructions", ""),
                        notes=subsection.get("notes"),
                        prior_context=prior_context,
                        resolved_data_source_config=progress.resolved_data_source_config,
                        formatting_profile=formatting_profile,
                    )

                # Save the generated content (with generated title if appropriate)
                save_subsection_version(
                    subsection_id=progress.subsection_id,
                    content=content,
                    content_type=content_type,
                    generated_by="agent",
                    title=generated_title if not progress.title else None,
                    generation_context={
                        "batch_job_id": job.job_id,
                        "generation_index": i,
                        "resolved_data_source_config": progress.resolved_data_source_config,
                        "dependency_subsection_ids": progress.dependency_subsection_ids,
                    },
                )

                # Add to accumulated context
                display_title = progress.title or generated_title or f"Subsection {label}"
                context_summary = content
                if content_type == "json":
                    try:
                        parsed_payload = json.loads(content)
                        if isinstance(parsed_payload, dict):
                            context_summary = _summarize_chart_payload(parsed_payload)
                    except (TypeError, ValueError):
                        context_summary = content
                context_entry = _build_generation_context_entry(
                    progress.section_title,
                    display_title,
                    context_summary,
                    subsection_id=progress.subsection_id,
                )
                job.generated_context.append(context_entry)
                generated_context_by_subsection_id[progress.subsection_id] = context_entry

                progress.status = GenerationStatus.COMPLETED
                progress.completed_at = datetime.utcnow()

            except Exception as e:
                progress.status = GenerationStatus.FAILED
                progress.error = str(e)
                progress.completed_at = datetime.utcnow()
                # Continue with next subsection even if one fails

        job.status = GenerationStatus.COMPLETED
        job.completed_at = datetime.utcnow()

    except Exception as e:
        job.status = GenerationStatus.FAILED
        job.error = str(e)
        job.completed_at = datetime.utcnow()


def _build_prior_context(generated: list[dict], max_items: int = 5) -> str:
    """Build context string from previously generated content."""
    if not generated:
        return ""

    lines = ["## Previously Generated Content (for coherence)"]
    window = generated[-max_items:] if max_items > 0 else generated
    for item in window:
        lines.append(f"\n### {item['section']} - {item['subsection']}")
        lines.append(item['content_summary'])

    return "\n".join(lines)


def _load_subsection_context_entry(subsection_id: str) -> Optional[dict]:
    """Load latest saved subsection content and format it for generation context."""
    subsection = get_subsection(subsection_id, include_versions=False)
    if "error" in subsection:
        return None

    content = subsection.get("content")
    if not isinstance(content, str) or not content.strip():
        return None

    content_summary = content
    if subsection.get("content_type") == "json":
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and parsed.get("kind") == "chart":
                chart = parsed.get("chart") if isinstance(parsed.get("chart"), dict) else {}
                series = chart.get("series") if isinstance(chart.get("series"), list) else []
                content_summary = (
                    f"Chart subsection: {parsed.get('title') or 'Untitled chart'} "
                    f"({len(series)} series)"
                )
        except (TypeError, ValueError):
            content_summary = content

    section_title = subsection.get("section_title") or "Section"
    label = position_to_label(subsection.get("position", 1))
    subsection_title = subsection.get("title") or f"Subsection {label}"
    return _build_generation_context_entry(
        section_title,
        subsection_title,
        content_summary,
        subsection_id=subsection_id,
    )


def _build_dependency_context_from_ids(
    dependency_subsection_ids: list[str],
    generated_context_by_subsection_id: dict[str, dict],
    cached_subsection_context: dict[str, Optional[dict]],
) -> str:
    """Build prior context from explicit subsection dependencies."""
    if not dependency_subsection_ids:
        return ""

    dependency_entries: list[dict] = []
    for dependency_subsection_id in dependency_subsection_ids:
        entry = generated_context_by_subsection_id.get(dependency_subsection_id)
        if entry is None:
            if dependency_subsection_id not in cached_subsection_context:
                cached_subsection_context[dependency_subsection_id] = _load_subsection_context_entry(
                    dependency_subsection_id
                )
            entry = cached_subsection_context.get(dependency_subsection_id)
        if entry:
            dependency_entries.append(entry)

    if not dependency_entries:
        return ""

    return _build_prior_context(dependency_entries, max_items=len(dependency_entries))


def _apply_title_case_mode(value: str, mode: str | None) -> str:
    """Apply configured title casing mode to a string."""
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    if not normalized:
        return normalized

    if mode == "upper":
        return normalized.upper()
    if mode == "sentence":
        return normalized[0].upper() + normalized[1:]
    if mode == "title":
        return normalized.title()
    return normalized


def _build_formatting_brief(formatting_profile: dict | None) -> str:
    """Build concise generation style guidance from template formatting settings."""
    if not isinstance(formatting_profile, dict):
        return ""

    font_family = formatting_profile.get("font_family") or "default sans-serif"
    line_height = formatting_profile.get("line_height") or 1.6
    section_case = formatting_profile.get("section_title_case") or "title"
    subsection_case = formatting_profile.get("subsection_title_case") or "title"
    accent_color = formatting_profile.get("accent_color") or "#2563EB"
    body_color = formatting_profile.get("body_color") or "#1F2937"

    return (
        "## Formatting Guidance\n"
        f"- Keep writing style compatible with font family: {font_family}\n"
        f"- Aim for readability with roughly line-height {line_height}\n"
        f"- Section title case mode: {section_case}\n"
        f"- Subsection title case mode: {subsection_case}\n"
        f"- Accent color reference: {accent_color}\n"
        f"- Body color reference: {body_color}"
    )


def _to_float(value: Any) -> float | None:
    """Best-effort conversion of numeric values to float."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        normalized = value.replace(",", "").replace("$", "").replace("%", "").strip()
        try:
            return float(normalized)
        except (TypeError, ValueError):
            return None
    return None


def _period_sort_key(period_label: str) -> tuple[int, int, str]:
    """Sort key for labels formatted like '2025 Q1'."""
    if not isinstance(period_label, str):
        return 0, 0, str(period_label)
    pieces = period_label.strip().split()
    if len(pieces) != 2:
        return 0, 0, period_label
    year_raw, quarter_raw = pieces
    try:
        year = int(year_raw)
    except (TypeError, ValueError):
        return 0, 0, period_label
    quarter_map = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
    quarter = quarter_map.get(quarter_raw.upper(), 0)
    return year, quarter, period_label


def _summarize_chart_payload(chart_payload: dict) -> str:
    """Generate a short text summary used in cross-subsection context."""
    chart = chart_payload.get("chart") if isinstance(chart_payload.get("chart"), dict) else {}
    series = chart.get("series") if isinstance(chart.get("series"), list) else []
    chart_type = chart.get("chart_type", "bar")
    return (
        f"Chart '{chart_payload.get('title') or 'Untitled'}' "
        f"({chart_type}, {len(series)} series)"
    )


def _build_chart_insights(
    chart_type: str,
    series: list[dict[str, Any]],
) -> list[str]:
    """Create concise, reader-facing insights for chart payloads."""
    if not isinstance(series, list) or not series:
        return []

    total_points = 0
    for series_item in series:
        points = series_item.get("points") if isinstance(series_item, dict) else None
        if isinstance(points, list):
            total_points += len(points)

    insights = [f"Covers {len(series)} series across {total_points} plotted points."]

    normalized_type = chart_type.lower() if isinstance(chart_type, str) else "bar"
    if normalized_type == "line":
        deltas: list[tuple[str, float]] = []
        for series_item in series:
            if not isinstance(series_item, dict):
                continue
            points = series_item.get("points") if isinstance(series_item.get("points"), list) else []
            if len(points) < 2:
                continue
            first_value = _to_float(points[0].get("y") if isinstance(points[0], dict) else None)
            last_value = _to_float(points[-1].get("y") if isinstance(points[-1], dict) else None)
            if first_value is None or last_value is None:
                continue
            deltas.append((str(series_item.get("name") or "Series"), last_value - first_value))

        if deltas:
            strongest = max(deltas, key=lambda item: item[1])
            weakest = min(deltas, key=lambda item: item[1])
            insights.append(
                f"Strongest momentum: {strongest[0]} ({strongest[1]:+,.2f} over the shown horizon)."
            )
            if weakest[0] != strongest[0]:
                insights.append(
                    f"Weakest momentum: {weakest[0]} ({weakest[1]:+,.2f} over the shown horizon)."
                )
        return insights

    # Bar/other chart types: use first series for quick top-bottom framing.
    first_series = series[0] if isinstance(series[0], dict) else None
    points = first_series.get("points") if isinstance(first_series, dict) and isinstance(first_series.get("points"), list) else []
    numeric_points: list[tuple[str, float]] = []
    for point in points:
        if not isinstance(point, dict):
            continue
        x_value = str(point.get("x", ""))
        y_value = _to_float(point.get("y"))
        if not x_value or y_value is None:
            continue
        numeric_points.append((x_value, y_value))

    if numeric_points:
        top = max(numeric_points, key=lambda item: item[1])
        bottom = min(numeric_points, key=lambda item: item[1])
        series_name = str(first_series.get("name") or "Primary series")
        insights.append(f"Highest in {series_name}: {top[0]} ({top[1]:,.2f}).")
        if top[0] != bottom[0]:
            insights.append(f"Lowest in {series_name}: {bottom[0]} ({bottom[1]:,.2f}).")

    return insights


def _score_chart_payload(chart_payload: dict | None) -> int:
    """
    Score a generated chart payload for selection among multiple candidates.

    Higher score favors richer charts (more series and plotted points).
    """
    if not isinstance(chart_payload, dict):
        return 0
    chart = chart_payload.get("chart") if isinstance(chart_payload.get("chart"), dict) else {}
    series = chart.get("series") if isinstance(chart.get("series"), list) else []
    if not series:
        return 0

    point_count = 0
    for series_item in series:
        points = series_item.get("points") if isinstance(series_item, dict) else None
        if isinstance(points, list):
            point_count += len(points)

    return len(series) * 100 + point_count


def _build_chart_payload_for_input(
    input_config: dict,
    results: list[dict],
    visualization: dict | None,
    *,
    section_title: str,
    subsection_title: str | None,
) -> dict | None:
    """Build a normalized chart payload from raw retriever results."""
    if not results:
        return None

    source_id = input_config.get("source_id")
    method_id = input_config.get("method_id")
    parameters = input_config.get("parameters") or {}
    viz = visualization or {}

    chart_type = viz.get("chart_type") or "bar"
    chart_title = viz.get("title") or subsection_title or f"{section_title} chart"
    metric_id = viz.get("metric_id")

    if source_id == "stock_prices":
        y_key = viz.get("y_key") or "close_price"
        x_points = []
        series_by_name: dict[str, list[dict[str, Any]]] = {}
        for result in results:
            if not isinstance(result, dict) or result.get("error"):
                continue
            bank_id = result.get("bank_id", "Unknown")
            period = result.get("period", "Unknown")
            y_value = _to_float(result.get(y_key))
            if y_value is None:
                continue

            if method_id == "trend":
                series_by_name.setdefault(str(bank_id), []).append({"x": str(period), "y": y_value})
            else:
                x_points.append({"x": str(bank_id), "y": y_value})

        if method_id == "trend":
            series = []
            for name, points in series_by_name.items():
                sorted_points = sorted(points, key=lambda item: _period_sort_key(str(item["x"])))
                series.append({"name": name, "points": sorted_points})
            if not series:
                return None
            chart_type = viz.get("chart_type") or "line"
            insights = _build_chart_insights(chart_type, series)
            return {
                "kind": "chart",
                "schema_version": 1,
                "title": chart_title,
                "chart": {
                    "chart_type": chart_type,
                    "x_label": "Period",
                    "y_label": y_key,
                    "series": series,
                },
                "source": {"source_id": source_id, "method_id": method_id},
                "insights": insights,
            }

        if not x_points:
            return None
        series = [{"name": y_key, "points": x_points}]
        chart_type = viz.get("chart_type") or "bar"
        insights = _build_chart_insights(chart_type, series)
        return {
            "kind": "chart",
            "schema_version": 1,
            "title": chart_title,
            "chart": {
                "chart_type": chart_type,
                "x_label": "Bank",
                    "y_label": y_key,
                    "series": series,
                },
                "source": {"source_id": source_id, "method_id": method_id},
                "insights": insights,
            }

    if source_id == "financials":
        metric_ids = parameters.get("metrics") if isinstance(parameters.get("metrics"), list) else []
        selected_metric_id = metric_id or (metric_ids[0] if metric_ids else None)

        # If multiple metrics are configured (and no explicit visualization.metric_id),
        # build a grouped multi-series bar chart across banks.
        if not metric_id and len(metric_ids) > 1:
            grouped_series: list[dict[str, Any]] = []
            for configured_metric_id in metric_ids:
                if not isinstance(configured_metric_id, str):
                    continue
                series_name = configured_metric_id
                points: list[dict[str, Any]] = []

                for result in results:
                    if not isinstance(result, dict) or result.get("error"):
                        continue
                    bank_id = result.get("bank_id", "Unknown")
                    metrics = result.get("metrics") if isinstance(result.get("metrics"), list) else []

                    metric_match = next(
                        (
                            metric
                            for metric in metrics
                            if isinstance(metric, dict) and metric.get("id") == configured_metric_id
                        ),
                        None,
                    )
                    if not isinstance(metric_match, dict):
                        continue

                    series_name = metric_match.get("name") or configured_metric_id
                    y_value = _to_float(metric_match.get("value"))
                    if y_value is None:
                        y_value = _to_float(metric_match.get("formatted"))
                    if y_value is None:
                        continue
                    points.append({"x": str(bank_id), "y": y_value})

                if points:
                    grouped_series.append({"name": str(series_name), "points": points})

            if grouped_series:
                chart_type = viz.get("chart_type") or "bar"
                insights = _build_chart_insights(chart_type, grouped_series)
                return {
                    "kind": "chart",
                    "schema_version": 1,
                    "title": chart_title,
                    "chart": {
                        "chart_type": chart_type,
                        "x_label": "Bank",
                        "y_label": "Value",
                        "series": grouped_series,
                    },
                    "source": {"source_id": source_id, "method_id": method_id},
                    "insights": insights,
                }

        per_bank_points: dict[str, list[dict[str, Any]]] = {}
        singleton_points: list[dict[str, Any]] = []
        metric_name = selected_metric_id or "metric"

        for result in results:
            if not isinstance(result, dict) or result.get("error"):
                continue

            bank_id = result.get("bank_id", "Unknown")
            period = result.get("period", "Unknown")
            metrics = result.get("metrics") if isinstance(result.get("metrics"), list) else []

            selected_metric = None
            if selected_metric_id:
                selected_metric = next(
                    (
                        metric
                        for metric in metrics
                        if isinstance(metric, dict) and metric.get("id") == selected_metric_id
                    ),
                    None,
                )
            if selected_metric is None and metrics:
                selected_metric = metrics[0] if isinstance(metrics[0], dict) else None
            if selected_metric is None:
                continue

            metric_name = selected_metric.get("name") or selected_metric.get("id") or metric_name
            y_value = _to_float(selected_metric.get("value"))
            if y_value is None:
                y_value = _to_float(selected_metric.get("formatted"))
            if y_value is None:
                continue

            per_bank_points.setdefault(str(bank_id), []).append({"x": str(period), "y": y_value})
            singleton_points.append({"x": str(bank_id), "y": y_value})

        if not per_bank_points:
            return None

        unique_periods = {
            point["x"]
            for points in per_bank_points.values()
            for point in points
        }

        if len(unique_periods) == 1 and len(singleton_points) > 1:
            chart_type = viz.get("chart_type") or "bar"
            chart_series = [{"name": metric_name, "points": singleton_points}]
            insights = _build_chart_insights(chart_type, chart_series)
            return {
                "kind": "chart",
                "schema_version": 1,
                "title": chart_title,
                "chart": {
                    "chart_type": chart_type,
                    "x_label": "Bank",
                    "y_label": metric_name,
                    "series": chart_series,
                },
                "source": {"source_id": source_id, "method_id": method_id},
                "insights": insights,
            }

        series = []
        for bank_name, points in per_bank_points.items():
            sorted_points = sorted(points, key=lambda item: _period_sort_key(str(item["x"])))
            series.append({"name": bank_name, "points": sorted_points})

        chart_type = viz.get("chart_type") or "line"
        insights = _build_chart_insights(chart_type, series)
        return {
            "kind": "chart",
            "schema_version": 1,
            "title": chart_title,
            "chart": {
                "chart_type": chart_type,
                "x_label": "Period",
                "y_label": metric_name,
                "series": series,
            },
            "source": {"source_id": source_id, "method_id": method_id},
            "insights": insights,
        }

    return None


async def _generate_chart_subsection_content(
    section_title: str,
    subsection_title: str | None,
    resolved_data_source_config: dict | None,
) -> tuple[str, str | None]:
    """
    Build chart subsection JSON content from configured data inputs.

    Returns:
        Tuple of (content_json, generated_title)
    """
    input_configs = extract_data_input_configs(resolved_data_source_config)
    visualization = extract_visualization_config(resolved_data_source_config)

    grouped_inputs: dict[tuple[str, str], dict[str, Any]] = {}
    for input_config in input_configs:
        source_id = input_config.get("source_id")
        method_id = input_config.get("method_id")
        if not isinstance(source_id, str) or not isinstance(method_id, str):
            continue

        group_key = (source_id, method_id)
        if group_key not in grouped_inputs:
            grouped_inputs[group_key] = {
                "representative_input": input_config,
                "results": [],
            }

        raw_results = await _fetch_raw_results_for_input(input_config)
        if isinstance(raw_results, list):
            grouped_inputs[group_key]["results"].extend(raw_results)

    best_payload: dict | None = None
    best_score = 0
    for grouped in grouped_inputs.values():
        payload = _build_chart_payload_for_input(
            input_config=grouped["representative_input"],
            results=grouped["results"],
            visualization=visualization,
            section_title=section_title,
            subsection_title=subsection_title,
        )
        score = _score_chart_payload(payload)
        if score > best_score:
            best_payload = payload
            best_score = score

    if best_payload:
        generated_title = (
            best_payload.get("title")
            if isinstance(best_payload.get("title"), str)
            else None
        )
        return json.dumps(best_payload), generated_title

    fallback_title = subsection_title or f"{section_title} chart"
    fallback_payload = {
        "kind": "chart",
        "schema_version": 1,
        "title": fallback_title,
        "chart": {
            "chart_type": visualization.get("chart_type", "bar") if isinstance(visualization, dict) else "bar",
            "x_label": "Category",
            "y_label": "Value",
            "series": [],
        },
        "insights": [
            "No chartable numeric data found from the configured inputs.",
            "Review data source parameters or choose a different retrieval method.",
        ],
    }
    return json.dumps(fallback_payload), fallback_title


async def _generate_subsection_content(
    template_name: str,
    section_title: str,
    subsection_label: str,
    subsection_title: Optional[str],
    instructions: str,
    notes: Optional[str],
    prior_context: str,
    resolved_data_source_config: Optional[dict] = None,
    formatting_profile: Optional[dict] = None,
) -> tuple[str, Optional[str]]:
    """
    Generate content for a single subsection using the LLM.

    Returns:
        Tuple of (content, generated_title)
    """
    # Build system prompt for generation
    title_context = f" ({subsection_title})" if subsection_title else ""
    formatting_brief = _build_formatting_brief(formatting_profile)
    system_prompt = f"""You are generating content for a financial report.

## Report: {template_name}
## Section: {section_title}
## Subsection: {subsection_label}{title_context}

{prior_context}

## Available Data
You can reference data from:
- Canadian Big 6 bank earnings call transcripts (RY, TD, BMO, BNS, CM, NA)
- Financial metrics (revenue, EPS, ROE, CET1 ratio, etc.)
- Stock price performance

{formatting_brief}

## Your Task
Generate the content based on the instructions provided. The content should be:
- Professional and suitable for a financial report
- Well-structured with appropriate markdown formatting
- Consistent with any previously generated content
- Focused and concise
- Use subsection titles that align with the configured casing guidance when possible
- Not include a top-level heading that duplicates the subsection title (the renderer already prints subsection titles)
- Use valid nested markdown lists when a numbered issue contains sub-points (do not flatten sub-points into the main numbering)
- For nested bullets under numbered items, indent bullet lines with 4 spaces

## Output Format
Return a JSON object with two fields:
1. "title": A short descriptive title for this subsection (3-8 words, or null if a title doesn't make sense)
2. "content": The content in markdown format

Example:
{{"title": "Q4 2024 Revenue Analysis", "content": "## Revenue Performance\\n\\nThe bank reported..."}}"""

    # Build user message with instructions
    user_message = f"""## Instructions
{instructions}"""

    if notes:
        user_message += f"""

## Additional Notes
{notes}"""

    data_context = ""
    if resolved_data_source_config:
        # Preferred path: use the subsection's configured source/method/parameters.
        data_context = await _fetch_data_from_config(resolved_data_source_config)

    if not data_context:
        # Backward-compatible fallback for legacy or unconfigured content.
        needs_data = any(keyword in instructions.lower() for keyword in [
            "earnings", "transcript", "revenue", "profit", "eps", "roe",
            "capital", "cet1", "stock", "price", "financial", "compare",
            "bank", "quarter", "q1", "q2", "q3", "q4", "fy2024", "fy2025"
        ])
        if needs_data:
            data_context = await _fetch_relevant_data(instructions)

    if data_context:
        user_message += f"""

## Relevant Data
{data_context}"""

    # Call LLM
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    response_text = response.choices[0].message.content or "{}"

    try:
        result = json.loads(response_text)
        content = result.get("content", response_text)
        title = result.get("title")
    except json.JSONDecodeError:
        # If JSON parsing fails, use the raw response as content
        content = response_text
        title = None

    if isinstance(title, str) and isinstance(formatting_profile, dict):
        title = _apply_title_case_mode(title, formatting_profile.get("subsection_title_case"))

    return content.strip(), title


def _to_period_query(
    bank_id: str,
    fiscal_year: Any,
    fiscal_quarter: Any,
) -> dict | None:
    """Normalize one bank/period query payload."""
    if not bank_id or fiscal_year is None or fiscal_quarter is None:
        return None

    try:
        year = int(fiscal_year)
    except (TypeError, ValueError):
        return None

    quarter = str(fiscal_quarter).strip().upper()
    if quarter not in {"Q1", "Q2", "Q3", "Q4"}:
        return None

    return {
        "bank_id": str(bank_id),
        "fiscal_year": year,
        "fiscal_quarter": quarter,
    }


def _build_queries_from_method_config(source_id: str, method_id: str, parameters: dict) -> list[dict]:
    """Build retriever query objects from configured method parameters."""
    queries: list[dict] = []

    if method_id == "by_quarter":
        query = _to_period_query(
            bank_id=parameters.get("bank_id"),
            fiscal_year=parameters.get("fiscal_year"),
            fiscal_quarter=parameters.get("fiscal_quarter"),
        )
        if query:
            queries.append(query)
        return queries

    if method_id == "compare_banks":
        bank_ids = parameters.get("bank_ids") or []
        if not isinstance(bank_ids, list):
            return queries
        for bank_id in bank_ids:
            query = _to_period_query(
                bank_id=bank_id,
                fiscal_year=parameters.get("fiscal_year"),
                fiscal_quarter=parameters.get("fiscal_quarter"),
            )
            if query:
                queries.append(query)
        return queries

    if source_id == "stock_prices" and method_id == "trend":
        bank_id = parameters.get("bank_id")
        periods = parameters.get("periods") or []
        if not bank_id or not isinstance(periods, list):
            return queries
        for period in periods:
            if not isinstance(period, dict):
                continue
            query = _to_period_query(
                bank_id=bank_id,
                fiscal_year=period.get("fiscal_year"),
                fiscal_quarter=period.get("fiscal_quarter"),
            )
            if query:
                queries.append(query)
        return queries

    # Forward-compatible generic path if query objects are pre-built.
    raw_queries = parameters.get("queries")
    if isinstance(raw_queries, list):
        for raw_query in raw_queries:
            if not isinstance(raw_query, dict):
                continue
            query = _to_period_query(
                bank_id=raw_query.get("bank_id"),
                fiscal_year=raw_query.get("fiscal_year"),
                fiscal_quarter=raw_query.get("fiscal_quarter"),
            )
            if query:
                queries.append(query)

    return queries


def _format_transcript_data_context(results: list[dict], section: str) -> str:
    """Render transcript retriever results for prompt context."""
    lines = [f"### Transcript Data (section: {section})"]
    added = 0
    for result in results[:4]:
        if result.get("error"):
            continue
        bank_id = result.get("bank_id", "UNKNOWN")
        period = result.get("period", "Unknown period")
        lines.append(f"- {bank_id} {period}")
        content = result.get("content") or result.get("management_discussion") or ""
        if content:
            lines.append(str(content)[:1400])
            added += 1
    return "\n".join(lines) if added else ""


def _format_financial_data_context(results: list[dict], metrics: list[str] | None) -> str:
    """Render financial retriever results for prompt context."""
    metric_label = ", ".join(metrics) if metrics else "default metrics"
    lines = [f"### Financial Metrics ({metric_label})"]
    added = 0
    for result in results[:8]:
        if result.get("error"):
            continue
        bank_id = result.get("bank_id", "UNKNOWN")
        period = result.get("period", "Unknown period")
        for metric in result.get("metrics", [])[:6]:
            metric_name = metric.get("name") or metric.get("id") or "Metric"
            metric_value = metric.get("formatted") or metric.get("value")
            lines.append(f"- {bank_id} {period} {metric_name}: {metric_value}")
            added += 1
    return "\n".join(lines) if added else ""


def _format_stock_data_context(results: list[dict]) -> str:
    """Render stock price retriever results for prompt context."""
    lines = ["### Stock Prices"]
    added = 0
    for result in results[:10]:
        if result.get("error"):
            continue
        bank_id = result.get("bank_id", "UNKNOWN")
        period = result.get("period", "Unknown period")
        close_price = result.get("close_price")
        qoq = result.get("qoq_change_pct")
        yoy = result.get("yoy_change_pct")
        if close_price is None:
            continue
        close_display = f"${float(close_price):.2f}" if isinstance(close_price, (int, float)) else str(close_price)
        qoq_display = f"{qoq:+.1f}%" if isinstance(qoq, (int, float)) else "n/a"
        yoy_display = f"{yoy:+.1f}%" if isinstance(yoy, (int, float)) else "n/a"
        lines.append(f"- {bank_id} {period}: {close_display} (QoQ: {qoq_display}, YoY: {yoy_display})")
        added += 1
    return "\n".join(lines) if added else ""


async def _fetch_data_for_input(input_config: dict) -> str:
    """Fetch retriever data for one resolved data input."""
    source_id = input_config.get("source_id")
    method_id = input_config.get("method_id")
    parameters = input_config.get("parameters") or {}
    if not source_id or not method_id or not isinstance(parameters, dict):
        return ""

    queries = _build_queries_from_method_config(source_id, method_id, parameters)
    if not queries:
        return ""

    try:
        if source_id == "transcripts":
            section = parameters.get("section")
            if section not in {"management_discussion", "qa", "both"}:
                section = "both"
            results = search_transcripts(queries=queries, section=section)
            return _format_transcript_data_context(results, section)

        if source_id == "financials":
            metrics = parameters.get("metrics")
            if not isinstance(metrics, list):
                metrics = None
            results = search_financials(queries=queries, metrics=metrics)
            return _format_financial_data_context(results, metrics)

        if source_id == "stock_prices":
            results = search_stock_prices(queries=queries)
            return _format_stock_data_context(results)
    except Exception:
        return ""

    return ""


async def _fetch_raw_results_for_input(input_config: dict) -> list[dict]:
    """Fetch raw retriever output for chart/table transformations."""
    source_id = input_config.get("source_id")
    method_id = input_config.get("method_id")
    parameters = input_config.get("parameters") or {}
    if not source_id or not method_id or not isinstance(parameters, dict):
        return []

    queries = _build_queries_from_method_config(source_id, method_id, parameters)
    if not queries:
        return []

    try:
        if source_id == "transcripts":
            section = parameters.get("section")
            if section not in {"management_discussion", "qa", "both"}:
                section = "both"
            results = search_transcripts(queries=queries, section=section)
            return results if isinstance(results, list) else []

        if source_id == "financials":
            metrics = parameters.get("metrics")
            if not isinstance(metrics, list):
                metrics = None
            results = search_financials(queries=queries, metrics=metrics)
            return results if isinstance(results, list) else []

        if source_id == "stock_prices":
            results = search_stock_prices(queries=queries)
            return results if isinstance(results, list) else []
    except Exception:
        return []

    return []


async def _fetch_data_from_config(resolved_data_source_config: dict) -> str:
    """
    Fetch retriever data from resolved subsection configuration.

    Expects fully resolved literal parameters (no variable bindings).
    """
    if not isinstance(resolved_data_source_config, dict):
        return ""

    input_configs = extract_data_input_configs(resolved_data_source_config)
    if not input_configs:
        return ""

    data_blocks: list[str] = []
    for index, input_config in enumerate(input_configs):
        input_context = await _fetch_data_for_input(input_config)
        if not input_context:
            continue

        source_id = input_config.get("source_id", "source")
        method_id = input_config.get("method_id", "method")
        header = f"## Data Input {index + 1}: {source_id}.{method_id}"
        data_blocks.append(f"{header}\n{input_context}")

    if not data_blocks:
        return ""

    return "\n\n".join(data_blocks)


async def _fetch_relevant_data(instructions: str) -> str:
    """Fetch relevant data based on instructions keywords."""
    data_parts = []
    instructions_lower = instructions.lower()

    # Determine which banks are mentioned
    banks = []
    bank_keywords = {
        "royal": "RY", "ry": "RY",
        "td": "TD", "toronto-dominion": "TD",
        "bmo": "BMO", "montreal": "BMO",
        "scotiabank": "BNS", "bns": "BNS", "scotia": "BNS",
        "cibc": "CM", "cm": "CM",
        "national": "NA", "na": "NA",
    }
    for keyword, bank_id in bank_keywords.items():
        if keyword in instructions_lower and bank_id not in banks:
            banks.append(bank_id)

    # Default to all banks if none specified
    if not banks:
        banks = ["RY", "TD", "BMO"]  # Top 3 by default

    # Determine quarter/period
    quarter = "Q4"  # Default to most recent
    if "q1" in instructions_lower:
        quarter = "Q1"
    elif "q2" in instructions_lower:
        quarter = "Q2"
    elif "q3" in instructions_lower:
        quarter = "Q3"

    fiscal_year = 2024
    if "2025" in instructions_lower or "fy2025" in instructions_lower:
        fiscal_year = 2025

    queries = [
        {
            "bank_id": bank_id,
            "fiscal_year": fiscal_year,
            "fiscal_quarter": quarter,
        }
        for bank_id in banks
    ]

    # Fetch transcripts if needed
    if any(kw in instructions_lower for kw in ["transcript", "earnings", "call", "management", "ceo", "cfo"]):
        try:
            transcript_results = search_transcripts(
                queries=queries[:2],  # keep context size manageable
                section="management_discussion",
            )
            for result in transcript_results:
                if result.get("error"):
                    continue
                bank_id = result.get("bank_id", "UNKNOWN")
                data_parts.append(
                    f"### {bank_id} FY{fiscal_year} {quarter} - Management Discussion"
                )
                content = result.get("content") or result.get("management_discussion") or ""
                if content:
                    data_parts.append(content[:1500])
        except Exception:
            pass

    # Fetch financials if needed
    if any(kw in instructions_lower for kw in ["revenue", "profit", "eps", "roe", "capital", "ratio", "financial", "metric"]):
        metrics = []
        if "revenue" in instructions_lower:
            metrics.append("total_revenue")
        if "eps" in instructions_lower:
            metrics.append("diluted_eps")
        if "roe" in instructions_lower:
            metrics.append("roe")
        if "capital" in instructions_lower or "cet1" in instructions_lower:
            metrics.append("cet1_ratio")
        if not metrics:
            metrics = ["total_revenue", "diluted_eps", "roe"]
        metrics = list(dict.fromkeys(metrics))

        try:
            financial_results = search_financials(
                queries=queries,
                metrics=metrics[:3],
            )
            data_parts.append(f"### Financial Metrics (FY{fiscal_year} {quarter})")
            for result in financial_results:
                if result.get("error"):
                    continue
                bank_id = result.get("bank_id", "UNKNOWN")
                for metric in result.get("metrics", [])[:3]:
                    metric_name = metric.get("name", metric.get("id", "Metric"))
                    metric_value = metric.get("formatted") or metric.get("value")
                    data_parts.append(f"- {bank_id} {metric_name}: {metric_value}")
        except Exception:
            pass

    # Fetch stock prices if needed
    if any(kw in instructions_lower for kw in ["stock", "price", "share", "performance"]):
        try:
            stock_results = search_stock_prices(
                queries=queries,
            )
            data_parts.append(f"### Stock Prices (FY{fiscal_year} {quarter})")
            for result in stock_results:
                if result.get("error"):
                    continue
                qoq = result.get("qoq_change_pct", 0) or 0
                yoy = result.get("yoy_change_pct", 0) or 0
                close_price = result.get("close_price")
                if close_price is None:
                    continue
                bank_id = result.get("bank_id", "UNKNOWN")
                try:
                    close_display = f"${float(close_price):.2f}"
                except (TypeError, ValueError):
                    close_display = str(close_price)
                try:
                    data_parts.append(
                        f"- {bank_id}: {close_display} "
                        f"(QoQ: {qoq:+.1f}%, YoY: {yoy:+.1f}%)"
                    )
                except (TypeError, ValueError):
                    data_parts.append(f"- {bank_id}: {close_display}")
        except Exception:
            pass

    return "\n".join(data_parts) if data_parts else ""
