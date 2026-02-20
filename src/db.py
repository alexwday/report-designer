"""
Database utilities with dual backend support.

Backends:
- sqlite (default): self-contained local file with automatic schema+seed bootstrap
- postgres: existing networked database mode
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:  # pragma: no cover - optional when running sqlite only
    psycopg2 = None
    RealDictCursor = None


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_SQLITE_PATH = _PROJECT_ROOT / "data" / "report_designer.db"

DB_BACKEND = os.getenv("DB_BACKEND", "sqlite").strip().lower()
SQLITE_DB_PATH = Path(os.getenv("SQLITE_DB_PATH", str(_DEFAULT_SQLITE_PATH)))

PG_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "34532")),
    "dbname": os.getenv("DB_NAME", "report_designer"),
}
if os.getenv("DB_USER"):
    PG_CONFIG["user"] = os.getenv("DB_USER")
if os.getenv("DB_PASSWORD"):
    PG_CONFIG["password"] = os.getenv("DB_PASSWORD")

_SQLITE_INIT_DONE = False
_SQLITE_INIT_LOCK = threading.Lock()

# sqlite JSON adapters/converters
sqlite3.register_adapter(dict, lambda value: json.dumps(value))
sqlite3.register_adapter(list, lambda value: json.dumps(value))
sqlite3.register_converter(
    "JSON",
    lambda value: json.loads(value.decode("utf-8")) if value else None,
)


def _is_sqlite() -> bool:
    return DB_BACKEND == "sqlite"


def _normalize_sql_for_sqlite(sql: str) -> str:
    """Convert Postgres-flavored SQL to sqlite-compatible SQL."""
    normalized = sql
    normalized = re.sub(r"%s", "?", normalized)
    # Strip Postgres casts (e.g., ::jsonb, ::text) before type rewrites.
    normalized = re.sub(r"::[A-Za-z_][A-Za-z0-9_]*", "", normalized)
    normalized = re.sub(r"\bUUID\b", "TEXT", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bJSONB\b", "JSON", normalized, flags=re.IGNORECASE)
    normalized = re.sub(
        r"\bTIMESTAMP\s+WITH\s+TIME\s+ZONE\b",
        "TEXT",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(r"\bNOW\(\)", "CURRENT_TIMESTAMP", normalized, flags=re.IGNORECASE)
    return normalized


def _adapt_sqlite_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    if isinstance(value, bool):
        return int(value)
    return value


def _adapt_sqlite_params(params: Any) -> Any:
    if params is None:
        return None
    if isinstance(params, dict):
        return {key: _adapt_sqlite_value(val) for key, val in params.items()}
    return tuple(_adapt_sqlite_value(val) for val in params)


class SQLiteCursorWrapper:
    """DB-API compatible cursor wrapper with SQL/param translation."""

    def __init__(self, cursor: sqlite3.Cursor):
        self._cursor = cursor

    def __enter__(self) -> "SQLiteCursorWrapper":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def execute(self, sql: str, params: Any = None) -> "SQLiteCursorWrapper":
        normalized = _normalize_sql_for_sqlite(sql)
        adapted_params = _adapt_sqlite_params(params)
        if adapted_params is None:
            self._cursor.execute(normalized)
        else:
            self._cursor.execute(normalized, adapted_params)
        return self

    def executemany(self, sql: str, seq_of_params: list[tuple[Any, ...]]) -> "SQLiteCursorWrapper":
        normalized = _normalize_sql_for_sqlite(sql)
        adapted = [_adapt_sqlite_params(params) for params in seq_of_params]
        self._cursor.executemany(normalized, adapted)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self) -> None:
        self._cursor.close()

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount


class SQLiteConnectionWrapper:
    """Connection wrapper exposing context-manager cursors like psycopg2."""

    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def cursor(self, *args, **kwargs) -> SQLiteCursorWrapper:
        return SQLiteCursorWrapper(self._connection.cursor())

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


def _sqlite_connect_raw() -> sqlite3.Connection:
    SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(SQLITE_DB_PATH),
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=False,
    )
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _create_sqlite_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS templates (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            created_by TEXT NOT NULL,
            output_format TEXT NOT NULL DEFAULT 'pdf' CHECK (output_format IN ('pdf', 'ppt')),
            orientation TEXT NOT NULL DEFAULT 'landscape' CHECK (orientation IN ('landscape', 'portrait')),
            formatting_profile JSON NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),
            is_shared INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_opened_at TEXT
        );

        CREATE TABLE IF NOT EXISTS sections (
            id TEXT PRIMARY KEY,
            template_id TEXT NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
            title TEXT,
            position INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(template_id, position)
        );

        CREATE TABLE IF NOT EXISTS subsections (
            id TEXT PRIMARY KEY,
            section_id TEXT NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
            title TEXT,
            position INTEGER NOT NULL DEFAULT 1,
            widget_type TEXT NOT NULL DEFAULT 'summary'
                CHECK (widget_type IN ('summary', 'key_points', 'table', 'chart', 'comparison', 'custom')),
            data_source_config JSON,
            notes TEXT,
            instructions TEXT,
            content TEXT,
            content_type TEXT DEFAULT 'markdown' CHECK (content_type IN ('text', 'markdown', 'html', 'json')),
            version_number INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(section_id, position)
        );

        CREATE TABLE IF NOT EXISTS subsection_versions (
            id TEXT PRIMARY KEY,
            subsection_id TEXT NOT NULL REFERENCES subsections(id) ON DELETE CASCADE,
            version_number INTEGER NOT NULL,
            instructions TEXT,
            notes TEXT,
            content TEXT,
            content_type TEXT DEFAULT 'markdown',
            generated_by TEXT DEFAULT 'agent' CHECK (generated_by IN ('agent', 'user_edit', 'import')),
            generation_context JSON,
            is_final INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(subsection_id, version_number)
        );

        CREATE TABLE IF NOT EXISTS data_source_registry (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            retrieval_methods JSON NOT NULL,
            suggested_widgets JSON,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS uploads (
            id TEXT PRIMARY KEY,
            template_id TEXT NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            content_type TEXT,
            size_bytes INTEGER,
            extracted_text TEXT,
            extraction_status TEXT DEFAULT 'pending',
            extraction_error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS template_versions (
            id TEXT PRIMARY KEY,
            template_id TEXT NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
            version_number INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            snapshot JSON NOT NULL,
            created_by TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(template_id, version_number)
        );

        CREATE TABLE IF NOT EXISTS template_generation_presets (
            template_id TEXT PRIMARY KEY REFERENCES templates(id) ON DELETE CASCADE,
            run_inputs JSON NOT NULL DEFAULT '{}',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            template_id TEXT NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(template_id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            surface TEXT NOT NULL DEFAULT 'main' CHECK (surface IN ('main', 'mini', 'agent_note')),
            section_id TEXT,
            subsection_id TEXT,
            sequence_number INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS transcripts (
            id TEXT PRIMARY KEY,
            bank_id TEXT NOT NULL CHECK (bank_id IN ('RY', 'TD', 'BMO', 'BNS', 'CM', 'NA')),
            fiscal_year INTEGER NOT NULL,
            fiscal_quarter TEXT NOT NULL CHECK (fiscal_quarter IN ('Q1', 'Q2', 'Q3', 'Q4')),
            section TEXT NOT NULL CHECK (section IN ('management_discussion', 'qa')),
            content_text TEXT NOT NULL,
            call_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(bank_id, fiscal_year, fiscal_quarter, section)
        );

        CREATE TABLE IF NOT EXISTS financials (
            id TEXT PRIMARY KEY,
            bank_id TEXT NOT NULL CHECK (bank_id IN ('RY', 'TD', 'BMO', 'BNS', 'CM', 'NA')),
            fiscal_year INTEGER NOT NULL,
            fiscal_quarter TEXT NOT NULL CHECK (fiscal_quarter IN ('Q1', 'Q2', 'Q3', 'Q4')),
            metric_id TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            value REAL,
            unit TEXT,
            formatted_value TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(bank_id, fiscal_year, fiscal_quarter, metric_id)
        );

        CREATE TABLE IF NOT EXISTS stock_prices (
            id TEXT PRIMARY KEY,
            bank_id TEXT NOT NULL CHECK (bank_id IN ('RY', 'TD', 'BMO', 'BNS', 'CM', 'NA')),
            fiscal_year INTEGER NOT NULL,
            fiscal_quarter TEXT NOT NULL CHECK (fiscal_quarter IN ('Q1', 'Q2', 'Q3', 'Q4')),
            close_price REAL,
            qoq_change_pct REAL,
            yoy_change_pct REAL,
            period_end_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(bank_id, fiscal_year, fiscal_quarter)
        );

        CREATE INDEX IF NOT EXISTS idx_templates_created_by ON templates(created_by);
        CREATE INDEX IF NOT EXISTS idx_templates_status ON templates(status);
        CREATE INDEX IF NOT EXISTS idx_templates_updated_at ON templates(updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_templates_is_shared ON templates(is_shared);

        CREATE INDEX IF NOT EXISTS idx_sections_template ON sections(template_id);
        CREATE INDEX IF NOT EXISTS idx_sections_position ON sections(template_id, position);
        CREATE INDEX IF NOT EXISTS idx_subsections_section ON subsections(section_id);
        CREATE INDEX IF NOT EXISTS idx_subsections_position ON subsections(section_id, position);
        CREATE INDEX IF NOT EXISTS idx_versions_subsection ON subsection_versions(subsection_id);
        CREATE INDEX IF NOT EXISTS idx_versions_number ON subsection_versions(subsection_id, version_number DESC);
        CREATE INDEX IF NOT EXISTS idx_registry_category ON data_source_registry(category);
        CREATE INDEX IF NOT EXISTS idx_registry_active ON data_source_registry(is_active);
        CREATE INDEX IF NOT EXISTS idx_uploads_template_id ON uploads(template_id);
        CREATE INDEX IF NOT EXISTS idx_template_versions_template_id ON template_versions(template_id, version_number DESC);
        CREATE INDEX IF NOT EXISTS idx_template_generation_presets_updated_at ON template_generation_presets(updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_conversations_template ON conversations(template_id);
        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_messages_sequence ON messages(conversation_id, sequence_number);

        CREATE INDEX IF NOT EXISTS idx_transcripts_bank ON transcripts(bank_id);
        CREATE INDEX IF NOT EXISTS idx_transcripts_period ON transcripts(fiscal_year, fiscal_quarter);
        CREATE INDEX IF NOT EXISTS idx_transcripts_section ON transcripts(section);
        CREATE INDEX IF NOT EXISTS idx_transcripts_bank_period ON transcripts(bank_id, fiscal_year, fiscal_quarter);

        CREATE INDEX IF NOT EXISTS idx_financials_bank ON financials(bank_id);
        CREATE INDEX IF NOT EXISTS idx_financials_period ON financials(fiscal_year, fiscal_quarter);
        CREATE INDEX IF NOT EXISTS idx_financials_metric ON financials(metric_id);
        CREATE INDEX IF NOT EXISTS idx_financials_bank_period ON financials(bank_id, fiscal_year, fiscal_quarter);

        CREATE INDEX IF NOT EXISTS idx_stock_bank ON stock_prices(bank_id);
        CREATE INDEX IF NOT EXISTS idx_stock_period ON stock_prices(fiscal_year, fiscal_quarter);
        CREATE INDEX IF NOT EXISTS idx_stock_bank_period ON stock_prices(bank_id, fiscal_year, fiscal_quarter);

        CREATE TRIGGER IF NOT EXISTS trg_templates_updated_at
        AFTER UPDATE ON templates
        FOR EACH ROW
        BEGIN
            UPDATE templates SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;

        CREATE TRIGGER IF NOT EXISTS trg_sections_updated_at
        AFTER UPDATE ON sections
        FOR EACH ROW
        BEGIN
            UPDATE sections SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;

        CREATE TRIGGER IF NOT EXISTS trg_subsections_updated_at
        AFTER UPDATE ON subsections
        FOR EACH ROW
        BEGIN
            UPDATE subsections SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;

        CREATE TRIGGER IF NOT EXISTS trg_uploads_updated_at
        AFTER UPDATE ON uploads
        FOR EACH ROW
        BEGIN
            UPDATE uploads SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;

        CREATE TRIGGER IF NOT EXISTS trg_registry_updated_at
        AFTER UPDATE ON data_source_registry
        FOR EACH ROW
        BEGIN
            UPDATE data_source_registry SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
        """
    )
    conn.commit()


def _load_python_constant(module_path: Path, constant_name: str, default: Any) -> Any:
    if not module_path.exists():
        return default

    module_name = f"_bootstrap_{module_path.stem}_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        return default

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, constant_name, default)


def _seed_transcripts(conn: sqlite3.Connection) -> None:
    data_file = _PROJECT_ROOT / "scripts" / "database" / "data" / "transcripts.json"
    if not data_file.exists():
        return

    payload = json.loads(data_file.read_text(encoding="utf-8"))
    records: list[tuple[Any, ...]] = []
    for item in payload:
        bank_id = item["bank_id"]
        fiscal_year = item["fiscal_year"]
        fiscal_quarter = item["fiscal_quarter"]
        call_date = item.get("call_date")
        for section, content in item.get("sections", {}).items():
            record_id = f"{bank_id}_{fiscal_year}_{fiscal_quarter}_{section}"
            records.append(
                (
                    record_id,
                    bank_id,
                    fiscal_year,
                    fiscal_quarter,
                    section,
                    content,
                    call_date,
                )
            )

    if not records:
        return

    conn.executemany(
        """
        INSERT INTO transcripts (
            id, bank_id, fiscal_year, fiscal_quarter, section, content_text, call_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            content_text = excluded.content_text,
            call_date = excluded.call_date
        """,
        records,
    )


def _seed_financials(conn: sqlite3.Connection) -> None:
    data_file = _PROJECT_ROOT / "scripts" / "database" / "data" / "financials.json"
    metrics_file = _PROJECT_ROOT / "scripts" / "database" / "metrics.py"
    if not data_file.exists():
        return

    metrics = _load_python_constant(metrics_file, "METRICS", [])
    metric_lookup = {metric.get("id"): metric for metric in metrics if isinstance(metric, dict)}

    payload = json.loads(data_file.read_text(encoding="utf-8"))
    records: list[tuple[Any, ...]] = []
    for item in payload:
        bank_id = item["bank_id"]
        fiscal_year = item["fiscal_year"]
        fiscal_quarter = item["fiscal_quarter"]
        for metric_id, metric_payload in item.get("metrics", {}).items():
            metric_meta = metric_lookup.get(metric_id, {})
            records.append(
                (
                    f"{bank_id}_{fiscal_year}_{fiscal_quarter}_{metric_id}",
                    bank_id,
                    fiscal_year,
                    fiscal_quarter,
                    metric_id,
                    metric_meta.get("name", metric_id),
                    metric_payload.get("value"),
                    metric_meta.get("unit", ""),
                    metric_payload.get("formatted"),
                )
            )

    if not records:
        return

    conn.executemany(
        """
        INSERT INTO financials (
            id, bank_id, fiscal_year, fiscal_quarter, metric_id,
            metric_name, value, unit, formatted_value
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            metric_name = excluded.metric_name,
            value = excluded.value,
            unit = excluded.unit,
            formatted_value = excluded.formatted_value
        """,
        records,
    )


def _seed_stock_prices(conn: sqlite3.Connection) -> None:
    data_file = _PROJECT_ROOT / "scripts" / "database" / "data" / "stock_prices.json"
    if not data_file.exists():
        return

    payload = json.loads(data_file.read_text(encoding="utf-8"))
    records = [
        (
            f"{item['bank_id']}_{item['fiscal_year']}_{item['fiscal_quarter']}",
            item["bank_id"],
            item["fiscal_year"],
            item["fiscal_quarter"],
            item.get("close_price"),
            item.get("qoq_change_pct"),
            item.get("yoy_change_pct"),
            item.get("period_end_date"),
        )
        for item in payload
    ]

    if not records:
        return

    conn.executemany(
        """
        INSERT INTO stock_prices (
            id, bank_id, fiscal_year, fiscal_quarter,
            close_price, qoq_change_pct, yoy_change_pct, period_end_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            close_price = excluded.close_price,
            qoq_change_pct = excluded.qoq_change_pct,
            yoy_change_pct = excluded.yoy_change_pct,
            period_end_date = excluded.period_end_date
        """,
        records,
    )


def _seed_data_source_registry(conn: sqlite3.Connection) -> None:
    registry_file = _PROJECT_ROOT / "scripts" / "database" / "seed_registry.py"
    sources = _load_python_constant(registry_file, "DATA_SOURCES", [])
    if not sources:
        return

    records: list[tuple[Any, ...]] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        records.append(
            (
                source.get("id"),
                source.get("name"),
                source.get("description"),
                source.get("category"),
                json.dumps(source.get("retrieval_methods", [])),
                json.dumps(source.get("suggested_widgets", [])),
            )
        )

    if not records:
        return

    conn.executemany(
        """
        INSERT INTO data_source_registry (
            id, name, description, category, retrieval_methods, suggested_widgets
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            description = excluded.description,
            category = excluded.category,
            retrieval_methods = excluded.retrieval_methods,
            suggested_widgets = excluded.suggested_widgets,
            updated_at = CURRENT_TIMESTAMP
        """,
        records,
    )


def _build_chart_payload(
    title: str,
    *,
    chart_type: str,
    x_label: str,
    y_label: str,
    series: list[dict[str, Any]],
    insights: list[str],
) -> str:
    payload = {
        "kind": "chart",
        "title": title,
        "chart": {
            "chart_type": chart_type,
            "x_label": x_label,
            "y_label": y_label,
            "series": series,
        },
        "insights": insights,
    }
    return json.dumps(payload)


def _seed_demo_template(conn: sqlite3.Connection) -> None:
    """
    Seed one ready-to-view demo template with chart subsections.

    Behavior:
    - If the seeded demo template already exists but is outdated (<4 sections), upgrade it.
    - If no seeded demo exists, create it only when templates table is empty.
    - Never alter user-created templates.
    """
    demo_name = "Demo: Big 6 Earnings Dashboard"
    demo_description = "Prebuilt starter template with summary + chart subsections."

    cur = conn.cursor()

    cur.execute(
        """
        SELECT id
        FROM templates
        WHERE name = ? AND created_by = 'system_seed'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (demo_name,),
    )
    existing_demo = cur.fetchone()

    if existing_demo:
        template_id = str(existing_demo[0])
        cur.execute("SELECT COUNT(*) FROM sections WHERE template_id = ?", (template_id,))
        existing_section_count = int(cur.fetchone()[0] or 0)
        if existing_section_count >= 4:
            return

        cur.execute("DELETE FROM sections WHERE template_id = ?", (template_id,))
    else:
        cur.execute("SELECT COUNT(*) FROM templates")
        if int(cur.fetchone()[0] or 0) > 0:
            return
        template_id = str(uuid4())

    formatting_profile = {
        "theme_id": "executive_blue",
        "theme_name": "Executive Blue",
        "font_family": "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
        "title_font_size_pt": 20,
        "subsection_title_font_size_pt": 13,
        "body_font_size_pt": 11,
        "line_height": 1.6,
        "accent_color": "#1D4ED8",
        "heading_color": "#111827",
        "body_color": "#1F2937",
        "section_title_case": "title",
        "subsection_title_case": "title",
    }

    summary_content = """## Q1 2025 Snapshot

1. RBC and TD lead absolute net income among the Big 6 this quarter.
2. National Bank and Scotiabank show the strongest quarter-over-quarter stock momentum.
3. Capital ratios remain solid across all banks, with CET1 buffers generally above 12%.

Use this template as a starting point for your own report layout and prompts."""

    profitability_narrative = """### Profitability and Capital Readout

- Net income leadership remains concentrated in RBC and TD.
- CET1 levels are broadly stable and above regulatory minimums.
- Monitor earnings quality through margin sustainability and credit costs.
"""

    credit_narrative = """### Credit Quality Highlights

- PCL ratios have normalized versus prior-year stress periods.
- Relative movement suggests credit quality remains manageable in aggregate.
- Use this section to add management commentary from transcripts as context.
"""

    income_chart_content = _build_chart_payload(
        "Big 6 Net Income (Q1 2025)",
        chart_type="bar",
        x_label="Bank",
        y_label="CAD Billions",
        series=[
            {
                "name": "Net Income",
                "points": [
                    {"x": "RY", "y": 4.1},
                    {"x": "TD", "y": 3.8},
                    {"x": "BMO", "y": 2.0},
                    {"x": "BNS", "y": 1.9},
                    {"x": "CM", "y": 1.8},
                    {"x": "NA", "y": 1.0},
                ],
            }
        ],
        insights=[
            "RBC and TD remain the top earners in absolute terms.",
            "Mid-pack separation between BMO, Scotiabank, and CIBC is narrow.",
            "National Bank is smaller in absolute income but continues to grow efficiently.",
        ],
    )

    stock_chart_content = _build_chart_payload(
        "Quarter-End Stock Price Trend",
        chart_type="line",
        x_label="Fiscal Quarter",
        y_label="Close Price (CAD)",
        series=[
            {
                "name": "RY",
                "points": [
                    {"x": "2024 Q4", "y": 129.2},
                    {"x": "2025 Q1", "y": 134.8},
                ],
            },
            {
                "name": "TD",
                "points": [
                    {"x": "2024 Q4", "y": 82.5},
                    {"x": "2025 Q1", "y": 84.9},
                ],
            },
            {
                "name": "NA",
                "points": [
                    {"x": "2024 Q4", "y": 103.4},
                    {"x": "2025 Q1", "y": 111.1},
                ],
            },
        ],
        insights=[
            "All three sample banks show positive QoQ movement.",
            "National Bank has the steepest slope over this window.",
            "Line chart layout is useful for multi-quarter trend narratives.",
        ],
    )

    cet1_chart_content = _build_chart_payload(
        "CET1 Ratio Comparison (Q1 2025)",
        chart_type="bar",
        x_label="Bank",
        y_label="CET1 Ratio (%)",
        series=[
            {
                "name": "CET1 Ratio",
                "points": [
                    {"x": "RY", "y": 13.2},
                    {"x": "TD", "y": 13.1},
                    {"x": "BMO", "y": 13.4},
                    {"x": "BNS", "y": 12.8},
                    {"x": "CM", "y": 12.9},
                    {"x": "NA", "y": 13.6},
                ],
            }
        ],
        insights=[
            "Capital buffers remain healthy across the Big 6.",
            "Dispersion is narrow, supporting peer comparability.",
            "Use alongside ROE to assess capital efficiency.",
        ],
    )

    pcl_trend_content = _build_chart_payload(
        "PCL Ratio Trend",
        chart_type="line",
        x_label="Fiscal Quarter",
        y_label="PCL Ratio (%)",
        series=[
            {
                "name": "RY",
                "points": [
                    {"x": "2024 Q3", "y": 0.30},
                    {"x": "2024 Q4", "y": 0.28},
                    {"x": "2025 Q1", "y": 0.27},
                ],
            },
            {
                "name": "TD",
                "points": [
                    {"x": "2024 Q3", "y": 0.34},
                    {"x": "2024 Q4", "y": 0.33},
                    {"x": "2025 Q1", "y": 0.31},
                ],
            },
            {
                "name": "BNS",
                "points": [
                    {"x": "2024 Q3", "y": 0.39},
                    {"x": "2024 Q4", "y": 0.37},
                    {"x": "2025 Q1", "y": 0.35},
                ],
            },
        ],
        insights=[
            "PCL ratios are trending lower in this sample window.",
            "Scotiabank remains elevated relative to peers but improving.",
            "Combine with transcript commentary for forward risk signals.",
        ],
    )

    stock_qoq_bar_content = _build_chart_payload(
        "QoQ Stock Performance",
        chart_type="bar",
        x_label="Bank",
        y_label="QoQ Change (%)",
        series=[
            {
                "name": "QoQ Change",
                "points": [
                    {"x": "RY", "y": 4.2},
                    {"x": "TD", "y": 2.9},
                    {"x": "BMO", "y": 3.8},
                    {"x": "BNS", "y": 5.1},
                    {"x": "CM", "y": 2.4},
                    {"x": "NA", "y": 7.5},
                ],
            }
        ],
        insights=[
            "National Bank and Scotiabank outperform on QoQ move.",
            "CIBC lags the group in this quarter.",
            "Use with valuation context before drawing directional conclusions.",
        ],
    )

    if existing_demo:
        cur.execute(
            """
            UPDATE templates
            SET description = ?,
                output_format = 'pdf',
                orientation = 'landscape',
                formatting_profile = ?,
                status = 'active',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                demo_description,
                json.dumps(formatting_profile),
                template_id,
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO templates (
                id, name, description, created_by, output_format, orientation, formatting_profile, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                template_id,
                demo_name,
                demo_description,
                "system_seed",
                "pdf",
                "landscape",
                json.dumps(formatting_profile),
                "active",
            ),
        )

    sections = [
        {
            "title": "Executive Summary",
            "subsections": [
                {
                    "title": "Quarter Snapshot",
                    "widget_type": "summary",
                    "data_source_config": {
                        "inputs": [
                            {
                                "source_id": "financials",
                                "method_id": "compare_banks",
                                "parameters": {
                                    "bank_ids": ["RY", "TD", "BMO", "BNS", "CM", "NA"],
                                    "fiscal_year": 2025,
                                    "fiscal_quarter": "Q1",
                                    "metrics": ["net_income", "roe", "cet1_ratio"],
                                },
                            }
                        ]
                    },
                    "notes": "Seeded summary block so the UI is populated on first run.",
                    "instructions": "Summarize the quarter in concise executive language.",
                    "content": summary_content,
                    "content_type": "markdown",
                },
            ],
        },
        {
            "title": "Profitability and Capital",
            "subsections": [
                {
                    "title": "Net Income Comparison",
                    "widget_type": "chart",
                    "data_source_config": {
                        "inputs": [
                            {
                                "source_id": "financials",
                                "method_id": "compare_banks",
                                "parameters": {
                                    "bank_ids": ["RY", "TD", "BMO", "BNS", "CM", "NA"],
                                    "fiscal_year": 2025,
                                    "fiscal_quarter": "Q1",
                                    "metrics": ["net_income"],
                                },
                            }
                        ],
                        "visualization": {"chart_type": "bar", "x_key": "bank_id", "y_key": "net_income"},
                    },
                    "notes": "Chart payload is pre-rendered so the component loads immediately.",
                    "instructions": "Compare net income across the selected banks.",
                    "content": income_chart_content,
                    "content_type": "json",
                },
                {
                    "title": "CET1 Comparison",
                    "widget_type": "chart",
                    "data_source_config": {
                        "inputs": [
                            {
                                "source_id": "financials",
                                "method_id": "compare_banks",
                                "parameters": {
                                    "bank_ids": ["RY", "TD", "BMO", "BNS", "CM", "NA"],
                                    "fiscal_year": 2025,
                                    "fiscal_quarter": "Q1",
                                    "metrics": ["cet1_ratio"],
                                },
                            }
                        ],
                        "visualization": {"chart_type": "bar", "x_key": "bank_id", "y_key": "cet1_ratio"},
                    },
                    "notes": "Capital section complements profitability view.",
                    "instructions": "Highlight comparative capital strength across peers.",
                    "content": cet1_chart_content,
                    "content_type": "json",
                },
                {
                    "title": "Profitability Commentary",
                    "widget_type": "summary",
                    "data_source_config": None,
                    "notes": "Narrative subsection for context around the metrics.",
                    "instructions": "Provide a concise interpretation of profitability and capital results.",
                    "content": profitability_narrative,
                    "content_type": "markdown",
                },
            ],
        },
        {
            "title": "Credit Quality",
            "subsections": [
                {
                    "title": "PCL Ratio Trend",
                    "widget_type": "chart",
                    "data_source_config": {
                        "inputs": [
                            {
                                "source_id": "financials",
                                "method_id": "compare_banks",
                                "parameters": {
                                    "bank_ids": ["RY", "TD", "BNS"],
                                    "fiscal_year": 2025,
                                    "fiscal_quarter": "Q1",
                                    "metrics": ["pcl_ratio"],
                                },
                            }
                        ],
                        "visualization": {"chart_type": "line", "x_key": "period", "y_key": "pcl_ratio"},
                    },
                    "notes": "Trend chart for credit normalization narrative.",
                    "instructions": "Track credit quality over recent quarters.",
                    "content": pcl_trend_content,
                    "content_type": "json",
                },
                {
                    "title": "Credit Narrative",
                    "widget_type": "summary",
                    "data_source_config": None,
                    "notes": "Use alongside transcript commentary for forward-looking language.",
                    "instructions": "Summarize key credit quality takeaways.",
                    "content": credit_narrative,
                    "content_type": "markdown",
                },
            ],
        },
        {
            "title": "Market Performance",
            "subsections": [
                {
                    "title": "Stock Trend",
                    "widget_type": "chart",
                    "data_source_config": {
                        "inputs": [
                            {
                                "source_id": "stock_prices",
                                "method_id": "trend",
                                "parameters": {
                                    "bank_id": "RY",
                                    "periods": [
                                        {"fiscal_year": 2024, "fiscal_quarter": "Q4"},
                                        {"fiscal_year": 2025, "fiscal_quarter": "Q1"},
                                    ],
                                },
                            }
                        ],
                        "visualization": {"chart_type": "line", "x_key": "period", "y_key": "close_price"},
                    },
                    "notes": "Swap bank IDs in config to tailor this trend panel.",
                    "instructions": "Show stock momentum over recent quarters.",
                    "content": stock_chart_content,
                    "content_type": "json",
                },
                {
                    "title": "QoQ Market Comparison",
                    "widget_type": "chart",
                    "data_source_config": {
                        "inputs": [
                            {
                                "source_id": "stock_prices",
                                "method_id": "compare_banks",
                                "parameters": {
                                    "bank_ids": ["RY", "TD", "BMO", "BNS", "CM", "NA"],
                                    "fiscal_year": 2025,
                                    "fiscal_quarter": "Q1",
                                },
                            }
                        ],
                        "visualization": {"chart_type": "bar", "x_key": "bank_id", "y_key": "qoq_change_pct"},
                    },
                    "notes": "Prebuilt cross-bank market move comparison.",
                    "instructions": "Compare quarter-over-quarter share-price movement.",
                    "content": stock_qoq_bar_content,
                    "content_type": "json",
                },
            ],
        },
    ]

    for section_position, section in enumerate(sections, start=1):
        section_id = str(uuid4())
        cur.execute(
            """
            INSERT INTO sections (id, template_id, title, position)
            VALUES (?, ?, ?, ?)
            """,
            (
                section_id,
                template_id,
                section["title"],
                section_position,
            ),
        )

        for subsection_position, subsection in enumerate(section["subsections"], start=1):
            cur.execute(
                """
                INSERT INTO subsections (
                    id, section_id, title, position, widget_type, data_source_config,
                    notes, instructions, content, content_type, version_number
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    section_id,
                    subsection["title"],
                    subsection_position,
                    subsection["widget_type"],
                    json.dumps(subsection["data_source_config"]) if subsection["data_source_config"] is not None else None,
                    subsection["notes"],
                    subsection["instructions"],
                    subsection["content"],
                    subsection["content_type"],
                    1,
                ),
            )


def _seed_sqlite_if_needed(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM transcripts")
    transcripts_count = cur.fetchone()[0]
    if transcripts_count == 0:
        _seed_transcripts(conn)

    cur.execute("SELECT COUNT(*) FROM financials")
    financials_count = cur.fetchone()[0]
    if financials_count == 0:
        _seed_financials(conn)

    cur.execute("SELECT COUNT(*) FROM stock_prices")
    stock_count = cur.fetchone()[0]
    if stock_count == 0:
        _seed_stock_prices(conn)

    cur.execute("SELECT COUNT(*) FROM data_source_registry")
    registry_count = cur.fetchone()[0]
    if registry_count == 0:
        _seed_data_source_registry(conn)

    _seed_demo_template(conn)

    conn.commit()


def initialize_database(force: bool = False) -> None:
    """Initialize schema/data for sqlite backend."""
    global _SQLITE_INIT_DONE

    if not _is_sqlite():
        return

    with _SQLITE_INIT_LOCK:
        if _SQLITE_INIT_DONE and not force:
            return

        conn = _sqlite_connect_raw()
        try:
            _create_sqlite_schema(conn)
            _seed_sqlite_if_needed(conn)
        finally:
            conn.close()

        _SQLITE_INIT_DONE = True


def ensure_column(cur, table_name: str, column_name: str, column_definition: str) -> None:
    """
    Add a column if missing for both sqlite and postgres backends.

    Args:
        cur: active DB cursor
        table_name: table to alter
        column_name: plain column name
        column_definition: SQL fragment after column name
    """
    if _is_sqlite():
        cur.execute(f"PRAGMA table_info({table_name})")
        existing = {row[1] for row in cur.fetchall()}
        if column_name in existing:
            return
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
        return

    cur.execute(
        f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_definition}"
    )


def get_connection():
    """Get a DB connection for the configured backend."""
    if _is_sqlite():
        initialize_database()
        return SQLiteConnectionWrapper(_sqlite_connect_raw())

    if DB_BACKEND != "postgres":
        raise ValueError(
            f"Unsupported DB_BACKEND '{DB_BACKEND}'. Expected 'sqlite' or 'postgres'."
        )

    if psycopg2 is None:
        raise RuntimeError("psycopg2 is required for postgres backend but is not installed")

    return psycopg2.connect(**PG_CONFIG)


def query(sql: str, params: tuple | None = None) -> list[dict]:
    """Execute query and return rows as dictionaries."""
    conn = get_connection()
    try:
        if _is_sqlite():
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                columns = [desc[0] for desc in (cur.description or [])]
                return [dict(zip(columns, row)) for row in rows]

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
