"""
PDF export functionality for Report Designer.

Uses WeasyPrint to convert HTML reports to PDF.
Simplified architecture: subsections render sequentially, full-width.
WeasyPrint handles page breaks with smart controls.
"""

import io
import json
import markdown
import re
from html import escape
from weasyprint import HTML, CSS

from ..db import get_connection
from ..workspace import get_template, get_sections


def get_preview_data(template_id: str) -> dict:
    """
    Get all data needed to preview/export a template.

    Returns:
        Template metadata and sections with subsections ordered by position
    """
    # Get template
    template_data = get_template(template_id)
    if "error" in template_data:
        return template_data

    # Extract just the template object (get_template returns {"template": {...}, "sections_summary": {...}})
    template = template_data.get("template", template_data)

    # Get sections with full content
    sections = get_sections(template_id, include_content=True)

    # Ensure subsections are sorted by position within each section
    for section in sections:
        subsections = section.get("subsections", [])
        section["subsections"] = sorted(subsections, key=lambda s: s.get("position", 0))

    return {
        "template": template,
        "sections": sections,
    }


def render_markdown(content: str) -> str:
    """Convert markdown content to HTML."""
    if not content:
        return ""
    return markdown.markdown(content, extensions=["tables", "fenced_code"])


def _build_chart_svg(chart: dict) -> str:
    """Render a simple SVG chart from normalized chart payload."""
    series = chart.get("series") if isinstance(chart.get("series"), list) else []
    chart_type = chart.get("chart_type") if isinstance(chart.get("chart_type"), str) else "bar"
    if not series:
        return ""

    categories: list[str] = []
    for item in series:
        points = item.get("points") if isinstance(item, dict) else None
        if not isinstance(points, list):
            continue
        for point in points:
            if not isinstance(point, dict):
                continue
            label = str(point.get("x", "")).strip()
            if label and label not in categories:
                categories.append(label)

    if not categories:
        return ""

    category_index = {label: idx for idx, label in enumerate(categories)}
    max_value = 0.0
    numeric_series: list[tuple[str, list[tuple[str, float]]]] = []
    for idx, item in enumerate(series):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or f"Series {idx + 1}")
        points = item.get("points") if isinstance(item.get("points"), list) else []
        normalized_points: list[tuple[str, float]] = []
        for point in points:
            if not isinstance(point, dict):
                continue
            x_label = str(point.get("x", "")).strip()
            if not x_label:
                continue
            try:
                y_value = float(point.get("y"))
            except (TypeError, ValueError):
                continue
            max_value = max(max_value, y_value)
            normalized_points.append((x_label, y_value))
        if normalized_points:
            numeric_series.append((name, normalized_points))

    if not numeric_series:
        return ""
    if max_value <= 0:
        max_value = 1.0

    width = 700
    height = 300
    margin_top = 20
    margin_right = 20
    margin_bottom = 70
    margin_left = 55
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    palette = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0d9488"]
    svg_parts: list[str] = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Chart">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="white"/>',
        f'<line x1="{margin_left}" y1="{margin_top + plot_height}" x2="{width - margin_right}" y2="{margin_top + plot_height}" stroke="#CBD5E1" stroke-width="1"/>',
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_height}" stroke="#CBD5E1" stroke-width="1"/>',
    ]

    if chart_type == "line":
        denom = (len(categories) - 1) if len(categories) > 1 else 1
        for series_index, (series_name, points) in enumerate(numeric_series):
            color = palette[series_index % len(palette)]
            polyline_points: list[str] = []
            for x_label, y_value in points:
                x_idx = category_index.get(x_label, 0)
                x = margin_left + (x_idx / denom) * plot_width
                y = margin_top + plot_height - (y_value / max_value) * plot_height
                polyline_points.append(f"{x:.1f},{y:.1f}")
            if len(polyline_points) >= 2:
                svg_parts.append(
                    f'<polyline fill="none" stroke="{color}" stroke-width="2.2" points="{" ".join(polyline_points)}"/>'
                )
            for x_label, y_value in points:
                x_idx = category_index.get(x_label, 0)
                x = margin_left + (x_idx / denom) * plot_width
                y = margin_top + plot_height - (y_value / max_value) * plot_height
                svg_parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.8" fill="{color}"/>')
    else:
        group_count = max(len(numeric_series), 1)
        category_width = plot_width / max(len(categories), 1)
        bar_width = max(category_width / (group_count + 1), 4)
        for series_index, (_series_name, points) in enumerate(numeric_series):
            color = palette[series_index % len(palette)]
            point_map = {label: value for label, value in points}
            for cat_idx, label in enumerate(categories):
                y_value = point_map.get(label)
                if y_value is None:
                    continue
                x = (
                    margin_left
                    + cat_idx * category_width
                    + (series_index + 0.5) * bar_width
                )
                bar_height = (y_value / max_value) * plot_height
                y = margin_top + plot_height - bar_height
                svg_parts.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="{color}" rx="1.5"/>'
                )

    for idx, label in enumerate(categories):
        if len(categories) > 1:
            x = margin_left + (idx / (len(categories) - 1)) * plot_width
        else:
            x = margin_left + plot_width / 2
        safe_label = escape(label)
        svg_parts.append(
            f'<text x="{x:.1f}" y="{height - 45}" text-anchor="middle" font-size="9" fill="#475569">{safe_label}</text>'
        )

    for tick in (0, 0.25, 0.5, 0.75, 1.0):
        y = margin_top + plot_height - (tick * plot_height)
        value = max_value * tick
        svg_parts.append(
            f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" stroke="#E2E8F0" stroke-width="0.8"/>'
        )
        svg_parts.append(
            f'<text x="{margin_left - 8}" y="{y + 3:.1f}" text-anchor="end" font-size="8.5" fill="#64748B">{value:.1f}</text>'
        )

    legend_x = margin_left
    legend_y = height - 24
    for index, (series_name, _points) in enumerate(numeric_series):
        color = palette[index % len(palette)]
        x = legend_x + index * 120
        safe_name = escape(series_name)
        svg_parts.append(f'<rect x="{x}" y="{legend_y - 9}" width="10" height="10" fill="{color}" rx="1"/>')
        svg_parts.append(
            f'<text x="{x + 14}" y="{legend_y}" font-size="9" fill="#334155">{safe_name}</text>'
        )

    svg_parts.append("</svg>")
    return "".join(svg_parts)


def render_chart_json(content: str) -> str:
    """Render structured chart JSON as HTML (SVG + optional notes)."""
    try:
        payload = json.loads(content)
    except (TypeError, ValueError):
        return ""

    if not isinstance(payload, dict) or payload.get("kind") != "chart":
        return ""

    chart = payload.get("chart") if isinstance(payload.get("chart"), dict) else {}
    chart_title = escape(str(payload.get("title") or "Chart"))
    chart_svg = _build_chart_svg(chart)
    if not chart_svg:
        chart_svg = "<p class='chart-empty'>No chart data available.</p>"

    insights_html = ""
    insights = payload.get("insights")
    if isinstance(insights, list):
        items = [f"<li>{escape(str(item))}</li>" for item in insights if str(item).strip()]
        if items:
            insights_html = (
                "<div class='chart-insights'><strong>Insights</strong><ul>"
                + "".join(items)
                + "</ul></div>"
            )

    return (
        "<div class='chart-wrapper'>"
        f"<div class='chart-title'>{chart_title}</div>"
        f"<div class='chart-svg'>{chart_svg}</div>"
        f"{insights_html}"
        "</div>"
    )


def _strip_redundant_leading_heading(content: str, subsection_title: str | None) -> str:
    """
    Remove a leading markdown heading when it duplicates the subsection title.

    This avoids duplicated title text in exports where the renderer already
    prints the subsection title above the markdown content.
    """
    if not content or not isinstance(subsection_title, str) or not subsection_title.strip():
        return content

    lines = content.splitlines()
    if not lines:
        return content

    heading_match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", lines[0])
    if not heading_match:
        return content

    heading_text = heading_match.group(1).strip().strip("#").strip()
    if heading_text.lower() != subsection_title.strip().lower():
        return content

    return "\n".join(lines[1:]).lstrip("\n")


def _normalize_nested_list_indentation(content: str) -> str:
    """
    Normalize likely nested bullets under ordered lists for Python-Markdown.

    Python-Markdown requires nested list items to be indented by 4 spaces.
    Model output frequently uses 2-3 spaces, which flattens nested bullets into
    the parent ordered list. We only adjust bullets that appear within an active
    ordered-list block.
    """
    if not content:
        return content

    lines = content.splitlines()
    normalized_lines: list[str] = []
    in_ordered_block = False

    for line in lines:
        stripped = line.strip()
        if re.match(r"^\d+\.\s+", stripped):
            in_ordered_block = True
            normalized_lines.append(line)
            continue

        if not stripped:
            normalized_lines.append(line)
            continue

        if in_ordered_block and re.match(r"^\s{1,3}-\s+", line):
            normalized_lines.append(f"    {stripped}")
            continue

        if in_ordered_block and not line.startswith(" "):
            in_ordered_block = False

        normalized_lines.append(line)

    return "\n".join(normalized_lines)


def _apply_title_case_mode(value: str | None, mode: str | None) -> str:
    """Apply configured casing mode to section/subsection titles."""
    if not isinstance(value, str):
        return ""
    normalized = value.strip()
    if not normalized:
        return ""
    if mode == "upper":
        return normalized.upper()
    if mode == "sentence":
        return normalized[0].upper() + normalized[1:]
    if mode == "title":
        return " ".join(
            word[:1].upper() + word[1:].lower()
            for word in normalized.split()
        )
    return normalized


def render_html(preview_data: dict) -> str:
    """
    Render preview data as HTML document.

    Clean professional output:
    - Each section starts on a new page
    - Subsections flow naturally without letter labels
    - Smart page breaks avoid orphaned headers and split content
    - Tables and lists kept together when possible

    Args:
        preview_data: Output from get_preview_data()

    Returns:
        Complete HTML document string
    """
    template = preview_data["template"]
    sections = preview_data["sections"]

    orientation = template.get("orientation", "portrait")
    is_landscape = orientation == "landscape"
    formatting_profile = (
        template.get("formatting_profile")
        if isinstance(template.get("formatting_profile"), dict)
        else {}
    )

    # Page size based on orientation
    page_width = "11in" if is_landscape else "8.5in"
    page_height = "8.5in" if is_landscape else "11in"

    font_family = formatting_profile.get("font_family") or "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    body_font_size = formatting_profile.get("body_font_size_pt") or 11
    section_title_size = formatting_profile.get("title_font_size_pt") or 20
    subsection_title_size = formatting_profile.get("subsection_title_font_size_pt") or 13
    line_height = formatting_profile.get("line_height") or 1.6
    accent_color = formatting_profile.get("accent_color") or "#2563eb"
    heading_color = formatting_profile.get("heading_color") or "#111827"
    body_color = formatting_profile.get("body_color") or "#1f2937"

    section_title_case = formatting_profile.get("section_title_case") or "title"
    subsection_title_case = formatting_profile.get("subsection_title_case") or "title"

    # Build sections HTML
    sections_html = []
    for i, section in enumerate(sections):
        section_html = render_section(
            section,
            i + 1,
            section_title_case=section_title_case,
            subsection_title_case=subsection_title_case,
        )
        sections_html.append(section_html)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{template.get('name', 'Report')}</title>
    <style>
        @page {{
            size: {page_width} {page_height};
            margin: 0.75in 0.75in 1in 0.75in;

            @bottom-center {{
                content: counter(page);
                font-size: 9pt;
                color: #6b7280;
            }}
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            font-family: {font_family};
            font-size: {body_font_size}pt;
            line-height: {line_height};
            color: {body_color};
            margin: 0;
            padding: 0;
        }}

        /* Section: starts on new page */
        .section {{
            page-break-before: always;
        }}

        .section:first-child {{
            page-break-before: avoid;
        }}

        .section-title {{
            font-size: {section_title_size}pt;
            font-weight: 600;
            color: {heading_color};
            margin: 0 0 0.3in 0;
            padding-bottom: 0.12in;
            border-bottom: 2px solid {accent_color};
            page-break-after: avoid;
            text-transform: none;
        }}

        .section-number {{
            color: #6b7280;
            font-weight: 400;
        }}

        /* Subsection styles - clean without labels */
        .subsection {{
            margin-bottom: 0.25in;
            page-break-inside: auto;
            break-inside: auto;
        }}

        .subsection:last-child {{
            margin-bottom: 0;
        }}

        /* Subsection title - only shown if present */
        .subsection-title {{
            font-size: {subsection_title_size}pt;
            font-weight: 600;
            color: {accent_color};
            margin: 0 0 0.1in 0;
            padding-bottom: 0.05in;
            border-bottom: 1px solid #dbeafe;
            page-break-after: avoid;
            break-after: avoid;
            text-transform: none;
        }}

        /* Content flows naturally */
        .subsection-content {{
            orphans: 3;
            widows: 3;
        }}

        .subsection-content p {{
            margin: 0 0 0.6em 0;
            text-align: justify;
        }}

        .subsection-content p:last-child {{
            margin-bottom: 0;
        }}

        /* Headers within content */
        .subsection-content h1,
        .subsection-content h2,
        .subsection-content h3,
        .subsection-content h4 {{
            page-break-after: avoid;
            margin: 0.8em 0 0.3em 0;
        }}

        .subsection-content h1 {{ font-size: 16pt; color: {heading_color}; }}
        .subsection-content h2 {{ font-size: 14pt; color: {heading_color}; }}
        .subsection-content h3 {{ font-size: 12pt; color: {heading_color}; }}
        .subsection-content h4 {{ font-size: 11pt; color: {heading_color}; font-weight: 600; }}

        /* Lists */
        .subsection-content ul, .subsection-content ol {{
            margin: 0.5em 0;
            padding-left: 1.5em;
            page-break-inside: auto;
        }}

        .subsection-content li {{
            margin: 0.3em 0;
        }}

        .subsection-content li::marker {{
            color: {accent_color};
        }}

        /* Tables - keep together */
        .subsection-content table {{
            border-collapse: collapse;
            width: 100%;
            margin: 0.6em 0;
            page-break-inside: avoid;
            font-size: 10pt;
        }}

        .subsection-content th, .subsection-content td {{
            border: 1px solid #d1d5db;
            padding: 0.4em 0.6em;
            text-align: left;
        }}

        .subsection-content th {{
            background: #f3f4f6;
            font-weight: 600;
            color: #374151;
        }}

        .subsection-content tr:nth-child(even) td {{
            background: #f9fafb;
        }}

        /* Code */
        .subsection-content code {{
            background: #f3f4f6;
            padding: 0.15em 0.3em;
            border-radius: 3px;
            font-family: 'SF Mono', Monaco, 'Courier New', monospace;
            font-size: 0.9em;
        }}

        .subsection-content pre {{
            background: #1f2937;
            color: #f9fafb;
            padding: 0.6em;
            border-radius: 4px;
            overflow-x: auto;
            page-break-inside: avoid;
            font-size: 9pt;
        }}

        .subsection-content pre code {{
            background: none;
            padding: 0;
        }}

        /* Blockquotes */
        .subsection-content blockquote {{
            border-left: 3px solid {accent_color};
            margin: 0.6em 0;
            padding: 0.3em 0 0.3em 1em;
            color: #4b5563;
            font-style: italic;
            page-break-inside: avoid;
        }}

        /* Horizontal rules as section dividers */
        .subsection-content hr {{
            border: none;
            border-top: 1px solid #e5e7eb;
            margin: 0.8em 0;
        }}

        /* Strong/emphasis */
        .subsection-content strong {{
            color: #111827;
        }}

        .chart-wrapper {{
            border: 1px solid #dbeafe;
            border-radius: 6px;
            padding: 0.12in;
            background: #f8fbff;
        }}

        .chart-title {{
            font-size: 11pt;
            font-weight: 600;
            color: #1e3a8a;
            margin-bottom: 0.08in;
        }}

        .chart-svg {{
            width: 100%;
            margin-bottom: 0.08in;
        }}

        .chart-svg svg {{
            width: 100%;
            height: auto;
        }}

        .chart-empty {{
            color: #64748b;
            font-style: italic;
            margin: 0;
        }}

        .chart-insights {{
            font-size: 9.5pt;
            color: #334155;
        }}

        .chart-insights ul {{
            margin: 0.25em 0 0 1.2em;
        }}

        /* Empty state - hidden in final PDF */
        .empty-subsection {{
            display: none;
        }}
    </style>
</head>
<body>
    {''.join(sections_html)}
</body>
</html>"""

    return html


def render_section(
    section: dict,
    number: int,
    *,
    section_title_case: str | None = None,
    subsection_title_case: str | None = None,
) -> str:
    """
    Render a section as HTML.

    Each section contains:
    - Section title with number
    - Subsections rendered sequentially (content flows naturally)
    """
    title = _apply_title_case_mode(
        section.get("title", f"Section {number}"),
        section_title_case,
    )
    subsections = section.get("subsections", [])

    # Render each subsection that has content
    subsections_html = []
    for subsection in subsections:
        content = subsection.get("content", "")
        if content and content.strip():
            subsection_html = render_subsection(
                subsection,
                title_case=subsection_title_case,
            )
            subsections_html.append(subsection_html)

    # If no content in any subsection, skip the section entirely in PDF
    if not subsections_html:
        return ""

    return f"""
    <div class="section">
        <h1 class="section-title">
            <span class="section-number">{number}.</span> {title}
        </h1>
        {''.join(subsections_html)}
    </div>
"""


def render_subsection(subsection: dict, *, title_case: str | None = None) -> str:
    """
    Render a single subsection as HTML.

    Clean output without letter labels:
    - Optional title (if provided)
    - Content rendered from markdown
    """
    title = _apply_title_case_mode(subsection.get("title"), title_case)
    content = subsection.get("content", "")
    content_type = subsection.get("content_type", "markdown")
    if content_type == "markdown":
        content = _strip_redundant_leading_heading(content, title)
        content = _normalize_nested_list_indentation(content)

    # Render content
    if content_type == "markdown":
        rendered_content = render_markdown(content)
    elif content_type == "json":
        chart_html = render_chart_json(content)
        rendered_content = chart_html if chart_html else f"<pre>{escape(content)}</pre>"
    else:
        rendered_content = f"<pre>{escape(content)}</pre>"

    # Build title if present
    if title:
        title_html = f'<h3 class="subsection-title">{title}</h3>'
    else:
        title_html = ""

    return f"""
    <div class="subsection">
        {title_html}
        <div class="subsection-content">
            {rendered_content}
        </div>
    </div>
"""


def generate_pdf(template_id: str) -> tuple[bytes, str]:
    """
    Generate PDF from template.

    Args:
        template_id: UUID of the template

    Returns:
        Tuple of (pdf_bytes, filename)
    """
    # Get preview data
    preview_data = get_preview_data(template_id)
    if "error" in preview_data:
        raise ValueError(preview_data["error"])

    # Render HTML
    html_content = render_html(preview_data)

    # Generate PDF
    html = HTML(string=html_content)
    pdf_buffer = io.BytesIO()
    html.write_pdf(pdf_buffer)
    pdf_bytes = pdf_buffer.getvalue()

    # Generate filename
    template_name = preview_data["template"].get("name", "report")
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in template_name)
    filename = f"{safe_name}.pdf"

    return pdf_bytes, filename
