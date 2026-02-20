"""
Data source registry tools for Report Designer.

Provides access to the registry of available data sources
that can be used to populate report subsections.
"""

from copy import deepcopy
from typing import Any

from ..db import get_connection

VARIABLE_BINDING_KEY = "$var"
VARIABLE_DEFAULT_KEY = "$default"
PERIOD_BINDING_KEY = "$period"
PERIOD_COUNT_KEY = "$count"

PERIOD_ANCHOR_YEAR_KEY = "period_fiscal_year"
PERIOD_ANCHOR_QUARTER_KEY = "period_fiscal_quarter"
VALID_FISCAL_QUARTERS = ("Q1", "Q2", "Q3", "Q4")

DATA_INPUTS_KEY = "inputs"
DEPENDENCIES_KEY = "dependencies"
DEPENDENCY_SECTION_IDS_KEY = "section_ids"
DEPENDENCY_SUBSECTION_IDS_KEY = "subsection_ids"
VISUALIZATION_KEY = "visualization"
VISUALIZATION_CHART_TYPE_KEY = "chart_type"
VISUALIZATION_TITLE_KEY = "title"
VISUALIZATION_X_KEY = "x_key"
VISUALIZATION_Y_KEY = "y_key"
VISUALIZATION_SERIES_KEY = "series_key"
VISUALIZATION_METRIC_ID_KEY = "metric_id"
VALID_CHART_TYPES = {"bar", "line"}


def get_section_period_anchor_year_key(section_id: str) -> str:
    """Build section-scoped run input key for base fiscal year."""
    return f"section_{section_id}_{PERIOD_ANCHOR_YEAR_KEY}"


def get_section_period_anchor_quarter_key(section_id: str) -> str:
    """Build section-scoped run input key for base fiscal quarter."""
    return f"section_{section_id}_{PERIOD_ANCHOR_QUARTER_KEY}"


def get_data_sources(
    category: str = None,
    active_only: bool = True,
) -> list[dict]:
    """
    Get available data sources from the registry.

    Args:
        category: Filter by category (optional)
        active_only: Only return active sources (default True)

    Returns:
        List of data sources with retrieval methods
    """
    conditions = []
    params = []

    if category:
        conditions.append("category = %s")
        params.append(category)
    if active_only:
        conditions.append("is_active = TRUE")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT id, name, description, category, retrieval_methods,
                       suggested_widgets, is_active, created_at
                FROM data_source_registry
                {where_clause}
                ORDER BY category, name
            """, tuple(params) if params else None)

            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "category": row[3],
                    "retrieval_methods": row[4],
                    "suggested_widgets": row[5],
                    "is_active": row[6],
                    "created_at": str(row[7]) if row[7] else None,
                }
                for row in cur.fetchall()
            ]
    finally:
        conn.close()


def _get_method_id(method: dict) -> Any:
    """Return a retrieval method identifier supporting legacy keys."""
    if not isinstance(method, dict):
        return None
    return method.get("method_id") or method.get("id")


def _get_param_key(param_def: dict) -> Any:
    """Return a parameter key supporting both key/name schemas."""
    if not isinstance(param_def, dict):
        return None
    return param_def.get("key") or param_def.get("name")


def is_variable_binding(value: Any) -> bool:
    """Return True if value is a variable binding object like {'$var': 'fiscal_year'}."""
    return (
        isinstance(value, dict)
        and isinstance(value.get(VARIABLE_BINDING_KEY), str)
        and bool(value.get(VARIABLE_BINDING_KEY).strip())
    )


def get_variable_name(value: Any) -> str | None:
    """Get variable name from a variable binding object."""
    if not is_variable_binding(value):
        return None
    return value[VARIABLE_BINDING_KEY].strip()


def is_period_binding(value: Any) -> bool:
    """Return True if value is a period binding object like {'$period': 'qoq.fiscal_year'}."""
    return (
        isinstance(value, dict)
        and isinstance(value.get(PERIOD_BINDING_KEY), str)
        and bool(value.get(PERIOD_BINDING_KEY).strip())
    )


def get_period_selector(value: Any) -> str | None:
    """Get selector from a period binding object."""
    if not is_period_binding(value):
        return None
    return value[PERIOD_BINDING_KEY].strip()


def _normalize_period_quarter(raw_quarter: Any) -> str | None:
    """Normalize quarter input to canonical Q1-Q4 format."""
    if not isinstance(raw_quarter, str):
        return None
    normalized = raw_quarter.strip().upper()
    if normalized in VALID_FISCAL_QUARTERS:
        return normalized
    return None


def _shift_period(fiscal_year: int, fiscal_quarter: str, offset_quarters: int) -> tuple[int, str]:
    """Shift a fiscal period by quarter offsets."""
    quarter_index = VALID_FISCAL_QUARTERS.index(fiscal_quarter)
    absolute = fiscal_year * 4 + quarter_index + offset_quarters
    shifted_year = absolute // 4
    shifted_quarter = VALID_FISCAL_QUARTERS[absolute % 4]
    return shifted_year, shifted_quarter


def _resolve_period_selector(
    selector: str,
    anchor_year: int,
    anchor_quarter: str,
    count: int | None = None,
) -> Any:
    """Resolve period selector into scalar/object/array value."""
    current = {
        "fiscal_year": anchor_year,
        "fiscal_quarter": anchor_quarter,
    }
    qoq_year, qoq_quarter = _shift_period(anchor_year, anchor_quarter, -1)
    qoq = {
        "fiscal_year": qoq_year,
        "fiscal_quarter": qoq_quarter,
    }
    yoy_year, yoy_quarter = _shift_period(anchor_year, anchor_quarter, -4)
    yoy = {
        "fiscal_year": yoy_year,
        "fiscal_quarter": yoy_quarter,
    }

    mapping = {
        "current": current,
        "last_quarter": qoq,
        "qoq": qoq,
        "yoy": yoy,
        "current.fiscal_year": current["fiscal_year"],
        "current.fiscal_quarter": current["fiscal_quarter"],
        "last_quarter.fiscal_year": qoq["fiscal_year"],
        "last_quarter.fiscal_quarter": qoq["fiscal_quarter"],
        "qoq.fiscal_year": qoq["fiscal_year"],
        "qoq.fiscal_quarter": qoq["fiscal_quarter"],
        "yoy.fiscal_year": yoy["fiscal_year"],
        "yoy.fiscal_quarter": yoy["fiscal_quarter"],
    }
    if selector in mapping:
        return mapping[selector]

    if selector == "trailing_quarters":
        trailing_count = count if count is not None else 4
        return [
            {
                "fiscal_year": year,
                "fiscal_quarter": quarter,
            }
            for year, quarter in (
                _shift_period(anchor_year, anchor_quarter, -(trailing_count - 1 - idx))
                for idx in range(trailing_count)
            )
        ]

    raise ValueError(f"Unsupported period selector '{selector}'")


def _validate_period_binding_for_type(expected_type: str, value: Any) -> str | None:
    """Validate period binding syntax + compatibility with expected parameter type."""
    selector = get_period_selector(value)
    key_label = PERIOD_BINDING_KEY
    if not selector:
        return f"Period binding must include non-empty '{key_label}'"

    count = value.get(PERIOD_COUNT_KEY) if isinstance(value, dict) else None
    if count is not None and (isinstance(count, bool) or not isinstance(count, int) or count < 1):
        return f"Period binding '{PERIOD_COUNT_KEY}' must be a positive integer"

    selector_shape: dict[str, str] = {
        "current": "object",
        "last_quarter": "object",
        "qoq": "object",
        "yoy": "object",
        "current.fiscal_year": "integer",
        "current.fiscal_quarter": "string",
        "last_quarter.fiscal_year": "integer",
        "last_quarter.fiscal_quarter": "string",
        "qoq.fiscal_year": "integer",
        "qoq.fiscal_quarter": "string",
        "yoy.fiscal_year": "integer",
        "yoy.fiscal_quarter": "string",
        "trailing_quarters": "array",
    }

    expected_shape = selector_shape.get(selector)
    if not expected_shape:
        return f"Unsupported period selector '{selector}'"

    if selector == "trailing_quarters" and count is None:
        # Default count=4 is supported, no error.
        pass

    if expected_type == "number":
        compatible = expected_shape in {"integer"}
    elif expected_type == "enum":
        compatible = expected_shape in {"string"}
    elif expected_type == "string":
        compatible = expected_shape in {"string"}
    else:
        compatible = expected_shape == expected_type

    if not compatible:
        return (
            f"Period selector '{selector}' is not compatible with parameter type '{expected_type}'"
        )

    return None


def _is_missing_value(value: Any) -> bool:
    """Treat empty/null values as missing for required parameter checks."""
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, list) and not value:
        return True
    if isinstance(value, dict) and not value:
        return True
    return False


def _validate_parameter_type(
    param_def: dict,
    value: Any,
    *,
    allow_variable_bindings: bool = True,
) -> str | None:
    """Validate one parameter value against a method parameter definition."""
    expected_type = (param_def.get("type") or "").lower()
    key = _get_param_key(param_def) or "unknown"

    if allow_variable_bindings and is_variable_binding(value):
        return None
    if allow_variable_bindings and is_period_binding(value):
        return _validate_period_binding_for_type(expected_type, value)

    if expected_type == "string":
        if not isinstance(value, str):
            return f"Parameter '{key}' must be a string"
        return None

    if expected_type == "enum":
        options = param_def.get("options") or param_def.get("enum") or []
        if not isinstance(value, str):
            return f"Parameter '{key}' must be one of: {', '.join(map(str, options))}"
        if options and value not in options:
            return f"Parameter '{key}' must be one of: {', '.join(map(str, options))}"
        return None

    if expected_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            return f"Parameter '{key}' must be an integer"
        return None

    if expected_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return f"Parameter '{key}' must be a number"
        return None

    if expected_type == "boolean":
        if not isinstance(value, bool):
            return f"Parameter '{key}' must be a boolean"
        return None

    if expected_type == "array":
        if not isinstance(value, list):
            return f"Parameter '{key}' must be an array"
        items_schema = param_def.get("items")
        if isinstance(items_schema, dict):
            allowed_items = items_schema.get("options") or items_schema.get("enum") or []
            if allowed_items:
                invalid = [item for item in value if item not in allowed_items]
                if invalid:
                    return (
                        f"Parameter '{key}' has invalid items: {invalid}. "
                        f"Allowed: {', '.join(map(str, allowed_items))}"
                    )
        return None

    if expected_type == "object":
        if not isinstance(value, dict):
            return f"Parameter '{key}' must be an object"
        return None

    # Unknown type: allow for forward-compatible schema evolution.
    return None


def _stable_unique_strings(values: Any) -> list[str]:
    """Normalize an arbitrary value to an ordered, de-duplicated list of strings."""
    if not isinstance(values, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        candidate = value.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized


def _normalize_visualization_config(raw_visualization: Any) -> tuple[list[str], dict | None]:
    """Validate optional chart visualization configuration."""
    if raw_visualization is None:
        return [], None
    if not isinstance(raw_visualization, dict):
        return [f"{VISUALIZATION_KEY} must be an object when provided"], None

    errors: list[str] = []
    normalized: dict[str, Any] = {}

    chart_type = raw_visualization.get(VISUALIZATION_CHART_TYPE_KEY)
    if chart_type is not None:
        if not isinstance(chart_type, str):
            errors.append(f"{VISUALIZATION_KEY}.{VISUALIZATION_CHART_TYPE_KEY} must be a string")
        else:
            chart_type_normalized = chart_type.strip().lower()
            if chart_type_normalized not in VALID_CHART_TYPES:
                errors.append(
                    f"{VISUALIZATION_KEY}.{VISUALIZATION_CHART_TYPE_KEY} must be one of: "
                    f"{', '.join(sorted(VALID_CHART_TYPES))}"
                )
            else:
                normalized[VISUALIZATION_CHART_TYPE_KEY] = chart_type_normalized

    for key in (
        VISUALIZATION_TITLE_KEY,
        VISUALIZATION_X_KEY,
        VISUALIZATION_Y_KEY,
        VISUALIZATION_SERIES_KEY,
        VISUALIZATION_METRIC_ID_KEY,
    ):
        value = raw_visualization.get(key)
        if value is None:
            continue
        if not isinstance(value, str):
            errors.append(f"{VISUALIZATION_KEY}.{key} must be a string")
            continue
        stripped = value.strip()
        if stripped:
            normalized[key] = stripped

    return errors, normalized if normalized else None


def _validate_single_data_input_config(
    data_input_config: dict,
    *,
    allow_variable_bindings: bool = True,
) -> tuple[list[str], dict]:
    """
    Validate one data input config against registry schema.

    Canonical shape:
        {"source_id": "...", "method_id": "...", "parameters": {...}}
    """
    errors: list[str] = []

    source_id = data_input_config.get("source_id")
    method_id = data_input_config.get("method_id")

    if not source_id:
        errors.append("Data input is missing source_id")
    if not method_id:
        errors.append("Data input is missing method_id")
    if errors:
        return errors, data_input_config

    source = get_data_source(source_id)
    if "error" in source:
        return [source["error"]], data_input_config

    methods = source.get("retrieval_methods") or []
    method = next((m for m in methods if _get_method_id(m) == method_id), None)
    if not method:
        return [f"Method '{method_id}' is not valid for data source '{source_id}'"], data_input_config

    parameter_defs = method.get("parameters") or []
    provided_parameters = data_input_config.get("parameters")
    if provided_parameters is None:
        provided_parameters = {}
    if not isinstance(provided_parameters, dict):
        return ["data input parameters must be an object"], data_input_config

    definitions_by_key = {
        key: param_def
        for param_def in parameter_defs
        if isinstance(param_def, dict) and (key := _get_param_key(param_def))
    }

    normalized_parameters = dict(provided_parameters)

    # Apply defaults from method schema when not explicitly provided.
    for key, param_def in definitions_by_key.items():
        if key not in normalized_parameters and "default" in param_def:
            normalized_parameters[key] = param_def["default"]

    for key, param_def in definitions_by_key.items():
        if param_def.get("required") and _is_missing_value(normalized_parameters.get(key)):
            errors.append(f"Required parameter '{key}' is missing")

    for key, value in normalized_parameters.items():
        param_def = definitions_by_key.get(key)
        if not param_def:
            errors.append(f"Unknown parameter '{key}' for method '{method_id}'")
            continue
        type_error = _validate_parameter_type(
            param_def,
            value,
            allow_variable_bindings=allow_variable_bindings,
        )
        if type_error:
            errors.append(type_error)

    normalized_config = {
        "source_id": source_id,
        "method_id": method_id,
    }
    if normalized_parameters:
        normalized_config["parameters"] = normalized_parameters

    return errors, normalized_config


def extract_data_input_configs(data_source_config: dict | None) -> list[dict]:
    """
    Return canonical input configs from data_source_config.

    Expected canonical shape:
        {"inputs": [ {"source_id": "...", "method_id": "...", "parameters": {...}}, ... ]}
    """
    if not isinstance(data_source_config, dict):
        return []

    raw_inputs = data_source_config.get(DATA_INPUTS_KEY)
    if not isinstance(raw_inputs, list):
        return []

    normalized_inputs: list[dict] = []
    for input_candidate in raw_inputs:
        if not isinstance(input_candidate, dict):
            continue

        source_id = input_candidate.get("source_id")
        method_id = input_candidate.get("method_id")
        if not source_id or not method_id:
            continue

        normalized_input = {
            "source_id": source_id,
            "method_id": method_id,
        }
        parameters = input_candidate.get("parameters")
        if isinstance(parameters, dict) and parameters:
            normalized_input["parameters"] = parameters

        normalized_inputs.append(normalized_input)

    return normalized_inputs


def extract_visualization_config(data_source_config: dict | None) -> dict | None:
    """Return normalized visualization config for chart-capable subsections."""
    if not isinstance(data_source_config, dict):
        return None

    visualization = data_source_config.get(VISUALIZATION_KEY)
    _errors, normalized = _normalize_visualization_config(visualization)
    return normalized


def extract_context_dependencies(data_source_config: dict | None) -> dict[str, list[str]]:
    """
    Return normalized context dependency references.

    Shape:
        {
            "section_ids": [...],
            "subsection_ids": [...],
        }
    """
    dependencies = {
        DEPENDENCY_SECTION_IDS_KEY: [],
        DEPENDENCY_SUBSECTION_IDS_KEY: [],
    }
    if not isinstance(data_source_config, dict):
        return dependencies

    raw_dependencies = data_source_config.get(DEPENDENCIES_KEY)
    if not isinstance(raw_dependencies, dict):
        return dependencies

    dependencies[DEPENDENCY_SECTION_IDS_KEY] = _stable_unique_strings(
        raw_dependencies.get(DEPENDENCY_SECTION_IDS_KEY)
    )
    dependencies[DEPENDENCY_SUBSECTION_IDS_KEY] = _stable_unique_strings(
        raw_dependencies.get(DEPENDENCY_SUBSECTION_IDS_KEY)
    )
    return dependencies


def validate_data_source_config(
    data_source_config: dict | None,
    *,
    allow_variable_bindings: bool = True,
) -> dict:
    """
    Validate subsection data source configuration against registry schema.

    Canonical shape:
        {
            "inputs": [ ... one or more data input configs ... ],
            "dependencies": {
                "section_ids": [...],
                "subsection_ids": [...],
            },
            "visualization": {
                "chart_type": "bar" | "line",
                "title": "...",
                "x_key": "...",
                "y_key": "...",
                "series_key": "...",
                "metric_id": "..."
            },
        }
    """
    if not isinstance(data_source_config, dict):
        return {
            "valid": False,
            "errors": ["Data source configuration must be an object"],
            "normalized_config": data_source_config,
        }

    errors: list[str] = []
    normalized_inputs: list[dict] = []
    raw_inputs = data_source_config.get(DATA_INPUTS_KEY)

    if not isinstance(raw_inputs, list):
        return {
            "valid": False,
            "errors": [f"Data source configuration must include an '{DATA_INPUTS_KEY}' array"],
            "normalized_config": data_source_config,
        }
    if not raw_inputs:
        return {
            "valid": False,
            "errors": [f"Data source configuration '{DATA_INPUTS_KEY}' cannot be empty"],
            "normalized_config": data_source_config,
        }

    for input_index, input_candidate in enumerate(raw_inputs):
        if not isinstance(input_candidate, dict):
            errors.append(f"inputs[{input_index}] must be an object")
            continue

        input_errors, normalized_input = _validate_single_data_input_config(
            input_candidate,
            allow_variable_bindings=allow_variable_bindings,
        )
        if input_errors:
            errors.extend([f"inputs[{input_index}]: {error}" for error in input_errors])
            continue

        normalized_inputs.append(normalized_input)

    dependencies = extract_context_dependencies(data_source_config)
    raw_dependencies = data_source_config.get(DEPENDENCIES_KEY)
    if raw_dependencies is not None and not isinstance(raw_dependencies, dict):
        errors.append("dependencies must be an object when provided")
    if isinstance(raw_dependencies, dict):
        raw_section_ids = raw_dependencies.get(DEPENDENCY_SECTION_IDS_KEY)
        if raw_section_ids is not None and not isinstance(raw_section_ids, list):
            errors.append("dependencies.section_ids must be an array of section ids")
        raw_subsection_ids = raw_dependencies.get(DEPENDENCY_SUBSECTION_IDS_KEY)
        if raw_subsection_ids is not None and not isinstance(raw_subsection_ids, list):
            errors.append("dependencies.subsection_ids must be an array of subsection ids")

    visualization_errors, normalized_visualization = _normalize_visualization_config(
        data_source_config.get(VISUALIZATION_KEY)
    )
    errors.extend(visualization_errors)

    normalized_config: dict[str, Any] = {
        DATA_INPUTS_KEY: normalized_inputs,
    }
    if dependencies[DEPENDENCY_SECTION_IDS_KEY] or dependencies[DEPENDENCY_SUBSECTION_IDS_KEY]:
        normalized_config[DEPENDENCIES_KEY] = dependencies
    if normalized_visualization:
        normalized_config[VISUALIZATION_KEY] = normalized_visualization

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "normalized_config": normalized_config,
    }


def get_data_source_method_details(source_id: str, method_id: str) -> dict:
    """
    Get data source + method details for a configured method.

    Returns:
        {
            "source": dict,
            "method": dict
        }
        or {"error": "..."}
    """
    source = get_data_source(source_id)
    if "error" in source:
        return {"error": source["error"]}

    methods = source.get("retrieval_methods") or []
    method = next((m for m in methods if _get_method_id(m) == method_id), None)
    if not method:
        return {"error": f"Method '{method_id}' is not valid for data source '{source_id}'"}

    return {"source": source, "method": method}


def collect_variable_bindings(value: Any) -> set[str]:
    """Collect all variable names referenced by nested variable binding objects."""
    names: set[str] = set()
    var_name = get_variable_name(value)
    if var_name:
        names.add(var_name)
        return names

    if isinstance(value, list):
        for item in value:
            names.update(collect_variable_bindings(item))
    elif isinstance(value, dict):
        for item in value.values():
            names.update(collect_variable_bindings(item))

    return names


def collect_period_bindings(value: Any) -> list[dict[str, Any]]:
    """Collect all period binding objects referenced in nested structures."""
    bindings: list[dict[str, Any]] = []
    if is_period_binding(value):
        selector = get_period_selector(value)
        if selector:
            binding_entry: dict[str, Any] = {
                PERIOD_BINDING_KEY: selector,
            }
            if isinstance(value, dict) and PERIOD_COUNT_KEY in value:
                binding_entry[PERIOD_COUNT_KEY] = value.get(PERIOD_COUNT_KEY)
            bindings.append(binding_entry)
        return bindings

    if isinstance(value, list):
        for item in value:
            bindings.extend(collect_period_bindings(item))
    elif isinstance(value, dict):
        for item in value.values():
            bindings.extend(collect_period_bindings(item))

    return bindings


def _resolve_bindings(
    value: Any,
    run_inputs: dict[str, Any],
    missing_vars: set[str],
    resolution_errors: list[str],
    section_id: str | None = None,
) -> Any:
    """Recursively resolve variable + period binding objects using provided run inputs."""
    var_name = get_variable_name(value)
    if var_name:
        if var_name in run_inputs:
            return run_inputs[var_name]
        if isinstance(value, dict) and VARIABLE_DEFAULT_KEY in value:
            return value[VARIABLE_DEFAULT_KEY]
        missing_vars.add(var_name)
        return value

    selector = get_period_selector(value)
    if selector:
        candidate_year_keys: list[str] = [PERIOD_ANCHOR_YEAR_KEY]
        candidate_quarter_keys: list[str] = [PERIOD_ANCHOR_QUARTER_KEY]
        if section_id:
            candidate_year_keys.insert(0, get_section_period_anchor_year_key(section_id))
            candidate_quarter_keys.insert(0, get_section_period_anchor_quarter_key(section_id))

        year_key_used = next((key for key in candidate_year_keys if key in run_inputs), candidate_year_keys[0])
        quarter_key_used = next((key for key in candidate_quarter_keys if key in run_inputs), candidate_quarter_keys[0])
        raw_year = run_inputs.get(year_key_used) if year_key_used in run_inputs else None
        raw_quarter = run_inputs.get(quarter_key_used) if quarter_key_used in run_inputs else None
        if raw_year is None:
            missing_vars.add(candidate_year_keys[0])
        if raw_quarter is None:
            missing_vars.add(candidate_quarter_keys[0])
        if raw_year is None or raw_quarter is None:
            return value

        try:
            anchor_year = int(raw_year)
        except (TypeError, ValueError):
            resolution_errors.append(
                f"Run input '{year_key_used}' must be an integer"
            )
            return value

        anchor_quarter = _normalize_period_quarter(raw_quarter)
        if not anchor_quarter:
            resolution_errors.append(
                f"Run input '{quarter_key_used}' must be one of {', '.join(VALID_FISCAL_QUARTERS)}"
            )
            return value

        raw_count = value.get(PERIOD_COUNT_KEY) if isinstance(value, dict) else None
        if raw_count is not None:
            if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count < 1:
                resolution_errors.append(
                    f"Period binding '{PERIOD_COUNT_KEY}' must be a positive integer"
                )
                return value

        try:
            return _resolve_period_selector(
                selector=selector,
                anchor_year=anchor_year,
                anchor_quarter=anchor_quarter,
                count=raw_count,
            )
        except ValueError as exc:
            resolution_errors.append(str(exc))
            return value

    if isinstance(value, list):
        return [
            _resolve_bindings(item, run_inputs, missing_vars, resolution_errors, section_id=section_id)
            for item in value
        ]
    if isinstance(value, dict):
        return {
            key: _resolve_bindings(
                item,
                run_inputs,
                missing_vars,
                resolution_errors,
                section_id=section_id,
            )
            for key, item in value.items()
        }
    return value


def resolve_data_source_config(
    data_source_config: dict | None,
    run_inputs: dict[str, Any] | None = None,
    section_id: str | None = None,
) -> dict:
    """
    Resolve variable bindings in data_source_config using run inputs.

    Returns:
        {
            "valid": bool,
            "errors": list[str],
            "resolved_config": dict | None,
            "missing_variables": list[str]
        }
    """
    validation = validate_data_source_config(
        data_source_config,
        allow_variable_bindings=True,
    )
    if not validation["valid"]:
        return {
            "valid": False,
            "errors": validation["errors"],
            "resolved_config": data_source_config,
            "missing_variables": [],
        }

    normalized = validation["normalized_config"]
    run_inputs = run_inputs or {}
    missing_vars: set[str] = set()
    resolution_errors: list[str] = []
    resolved = _resolve_bindings(
        deepcopy(normalized),
        run_inputs,
        missing_vars,
        resolution_errors,
        section_id=section_id,
    )

    if resolution_errors:
        return {
            "valid": False,
            "errors": resolution_errors,
            "resolved_config": resolved,
            "missing_variables": sorted(missing_vars),
        }

    if missing_vars:
        return {
            "valid": False,
            "errors": [f"Missing run input '{name}'" for name in sorted(missing_vars)],
            "resolved_config": resolved,
            "missing_variables": sorted(missing_vars),
        }

    resolved_validation = validate_data_source_config(
        resolved,
        allow_variable_bindings=False,
    )
    return {
        "valid": resolved_validation["valid"],
        "errors": resolved_validation["errors"],
        "resolved_config": resolved_validation["normalized_config"],
        "missing_variables": [],
    }


def get_data_source(source_id: str) -> dict:
    """
    Get a specific data source by ID.

    Args:
        source_id: Data source ID

    Returns:
        Data source details or error
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, description, category, retrieval_methods,
                       suggested_widgets, is_active
                FROM data_source_registry
                WHERE id = %s
            """, (source_id,))

            row = cur.fetchone()
            if not row:
                return {"error": f"Data source not found: {source_id}"}

            return {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "category": row[3],
                "retrieval_methods": row[4],
                "suggested_widgets": row[5],
                "is_active": row[6],
            }
    finally:
        conn.close()


# Tool definition for MCP server
TOOL_DEFINITION = {
    "name": "get_data_sources",
    "description": """Get available data sources from the registry.

Returns list of data sources with:
- Name and description
- Available retrieval methods
- Parameter requirements for each method
- Suggested widget types

Use this to understand what data is available and how to retrieve it.

Available categories: bank_data""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Filter by category (e.g., 'bank_data'). Optional."
            },
            "active_only": {
                "type": "boolean",
                "default": True,
                "description": "Only return active sources"
            }
        },
        "required": []
    }
}
