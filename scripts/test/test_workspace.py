"""
Test script for workspace tools.

Tests all workspace management tools against the Postgres database.
Run from project root: python scripts/test/test_workspace.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.workspace.templates import create_template, get_template, list_templates, update_template
from src.workspace.sections import create_section, get_sections, update_section, delete_section
from src.workspace.subsections import (
    get_subsection, update_notes, update_instructions,
    configure_subsection, save_subsection_version
)
from src.workspace.data_sources import get_data_sources


def test_data_sources():
    """Test data source registry."""
    print("\n" + "="*60)
    print("TEST: Data Sources Registry")
    print("="*60)

    # Get all data sources
    print("\n1. Get all data sources:")
    sources = get_data_sources()
    print(f"   Found {len(sources)} data source(s)")
    for src in sources:
        print(f"   - {src['id']}: {src['name']} ({src['category']})")
        methods = src.get('retrieval_methods', [])
        print(f"     Methods: {[m['method_id'] for m in methods]}")

    assert len(sources) == 3, f"Expected 3 sources, got {len(sources)}"
    print("   [PASS]")


def test_template_crud():
    """Test template create/read/update operations."""
    print("\n" + "="*60)
    print("TEST: Template CRUD")
    print("="*60)

    # Create a template
    print("\n1. Create template:")
    template = create_template(
        name="Test Report - Q1 2025",
        created_by="test_user",
        description="Test template for workspace tools",
        output_format="pdf",
        orientation="landscape"
    )
    print(f"   Created: {template['name']} (ID: {template['id'][:8]}...)")
    assert "id" in template
    assert template["name"] == "Test Report - Q1 2025"
    print("   [PASS]")

    template_id = template["id"]

    # Get template
    print("\n2. Get template:")
    result = get_template(template_id)
    print(f"   Retrieved: {result['template']['name']}")
    print(f"   Sections: {result['sections_summary']['count']}")
    assert result["template"]["id"] == template_id
    print("   [PASS]")

    # Update template
    print("\n3. Update template:")
    updated = update_template(
        template_id=template_id,
        description="Updated description"
    )
    print(f"   Updated description: {updated['description'][:30]}...")
    assert updated["description"] == "Updated description"
    print("   [PASS]")

    # List templates
    print("\n4. List templates:")
    templates = list_templates(created_by="test_user")
    print(f"   Found {len(templates)} template(s) for test_user")
    assert len(templates) >= 1
    print("   [PASS]")

    return template_id


def test_section_crud(template_id: str):
    """Test section create/read/update/delete operations."""
    print("\n" + "="*60)
    print("TEST: Section CRUD")
    print("="*60)

    # Create section
    print("\n1. Create section:")
    section1 = create_section(
        template_id=template_id,
        title="Executive Summary"
    )
    print(f"   Created: {section1['title']} at position {section1['position']}")
    print(f"   Subsections: {len(section1['subsections'])}")
    assert section1["title"] == "Executive Summary"
    assert len(section1["subsections"]) == 1
    print("   [PASS]")

    section1_id = section1["id"]
    subsection1_id = section1["subsections"][0]["id"]

    # Create second section
    print("\n2. Create section:")
    section2 = create_section(
        template_id=template_id,
        title="Financial Comparison"
    )
    print(f"   Created: {section2['title']} at position {section2['position']}")
    print(f"   Subsections: {len(section2['subsections'])}")
    assert len(section2["subsections"]) == 1
    print("   [PASS]")

    # Get sections
    print("\n3. Get sections:")
    sections = get_sections(template_id)
    print(f"   Found {len(sections)} section(s)")
    for s in sections:
        print(f"   - Position {s['position']}: {s['title']} ({len(s['subsections'])} subsections)")
    assert len(sections) == 2
    print("   [PASS]")

    # Update section
    print("\n4. Update section (change title):")
    updated = update_section(
        section_id=section1_id,
        title="Executive Summary - Updated"
    )
    print(f"   Updated title: {updated['title']}")
    assert "Updated" in updated["title"]
    print("   [PASS]")

    # Delete section
    print("\n5. Delete section:")
    result = delete_section(section_id=section2["id"])
    print(f"   Deleted: {result['deleted']}")
    sections = get_sections(template_id)
    assert len(sections) == 1
    print(f"   Remaining sections: {len(sections)}")
    print("   [PASS]")

    return section1_id, subsection1_id


def test_subsection_operations(subsection_id: str):
    """Test subsection notes, instructions, and versioning."""
    print("\n" + "="*60)
    print("TEST: Subsection Operations")
    print("="*60)

    # Get subsection
    print("\n1. Get subsection:")
    subsection = get_subsection(subsection_id)
    print(f"   Widget type: {subsection['widget_type']}")
    print(f"   Version: {subsection['version_number']}")
    print(f"   Versions in history: {len(subsection.get('versions', []))}")
    print("   [PASS]")

    # Update notes
    print("\n2. Update notes:")
    result = update_notes(
        subsection_id=subsection_id,
        notes="User prefers executive-friendly tone. Focus on key insights."
    )
    print(f"   Notes updated: {result['updated']}")
    print(f"   Notes preview: {result['notes'][:50]}...")
    assert result["updated"]
    print("   [PASS]")

    # Append to notes
    print("\n3. Append to notes:")
    result = update_notes(
        subsection_id=subsection_id,
        notes="Tried bullet points - user approved.",
        append=True
    )
    print(f"   Notes now: {len(result['notes'])} chars")
    assert "bullet points" in result["notes"]
    print("   [PASS]")

    # Update instructions
    print("\n4. Update instructions:")
    result = update_instructions(
        subsection_id=subsection_id,
        instructions="""Generate an executive summary with:
- 3-4 key bullet points highlighting main trends
- Focus on RY and TD performance
- Include QoQ comparisons
- Keep tone professional but accessible"""
    )
    print(f"   Instructions updated: {result['updated']}")
    print("   [PASS]")

    # Configure subsection
    print("\n5. Configure subsection (data source + widget):")
    result = configure_subsection(
        subsection_id=subsection_id,
        widget_type="key_points",
        data_source_config={
            "inputs": [
                {
                    "source_id": "financials",
                    "method_id": "compare_banks",
                    "parameters": {
                        "bank_ids": ["RY", "TD"],
                        "fiscal_year": 2025,
                        "fiscal_quarter": "Q1",
                        "metrics": ["net_income", "roe", "cet1_ratio"]
                    }
                }
            ]
        }
    )
    print(f"   Widget type: {result['widget_type']}")
    print(f"   Data source: {result['data_source_config']['inputs'][0]['source_id']}")
    assert result["widget_type"] == "key_points"
    print("   [PASS]")

    # Save content version
    print("\n6. Save subsection version:")
    version = save_subsection_version(
        subsection_id=subsection_id,
        content="""## Q1 2025 Executive Summary

- **RY**: Net income of $4.2B (+5% QoQ), ROE at 16.2%
- **TD**: Net income of $3.8B (-2% QoQ), ROE at 14.8%
- Both banks maintaining strong CET1 ratios above 12%
- Market conditions remain favorable for Canadian banking sector""",
        content_type="markdown",
        generated_by="agent",
        generation_context={"data_sources_used": ["financials"]}
    )
    print(f"   Created version {version['version_number']}")
    print(f"   Generated by: {version['generated_by']}")
    assert version["version_number"] == 1
    print("   [PASS]")

    # Save another version (iteration)
    print("\n7. Save revised version:")
    version2 = save_subsection_version(
        subsection_id=subsection_id,
        content="""## Q1 2025 Executive Summary

**Key Highlights:**

- **Royal Bank (RY)**: Strong quarter with net income of $4.2B (+5% QoQ)
  - ROE: 16.2% | CET1: 12.8%
- **TD Bank**: Solid performance with net income of $3.8B (-2% QoQ)
  - ROE: 14.8% | CET1: 12.5%

Both banks continue to demonstrate resilience with capital ratios well above regulatory requirements.""",
        content_type="markdown",
        generated_by="agent",
    )
    print(f"   Created version {version2['version_number']}")
    assert version2["version_number"] == 2
    print("   [PASS]")

    # Verify version history
    print("\n8. Verify version history:")
    subsection = get_subsection(subsection_id)
    print(f"   Current version: {subsection['version_number']}")
    print(f"   Versions in history: {len(subsection['versions'])}")
    for v in subsection["versions"]:
        print(f"   - v{v['version_number']}: {v['generated_by']} ({v['created_at'][:19]})")
    assert len(subsection["versions"]) == 2
    print("   [PASS]")

    # Mark as final
    print("\n9. Mark version as final:")
    final = save_subsection_version(
        subsection_id=subsection_id,
        content=subsection["content"],  # Keep same content
        is_final=True,
    )
    print(f"   Version {final['version_number']} marked as final: {final['is_final']}")
    assert final["is_final"]
    print("   [PASS]")


def test_full_workflow():
    """Test a complete workflow from template to content."""
    print("\n" + "="*60)
    print("TEST: Full Workflow")
    print("="*60)

    # 1. Check data sources
    sources = get_data_sources()
    print(f"\n1. Available data sources: {[s['id'] for s in sources]}")

    # 2. Create template
    template = create_template(
        name="Big 6 Banks Q1 2025 Analysis",
        created_by="analyst",
        description="Quarterly analysis of Canadian Big 6 banks"
    )
    print(f"2. Created template: {template['name']}")

    # 3. Add sections
    section = create_section(
        template_id=template["id"],
        title="Financial Overview"
    )
    print(f"3. Created section: {section['title']} with {len(section['subsections'])} subsections")

    # 4. Configure subsection
    main_subsection = section["subsections"][0]
    configure_subsection(
        subsection_id=main_subsection["id"],
        widget_type="table",
        data_source_config={
            "inputs": [
                {
                    "source_id": "financials",
                    "method_id": "compare_banks",
                    "parameters": {
                        "bank_ids": ["RY", "TD", "BMO", "BNS", "CM", "NA"],
                        "fiscal_year": 2025,
                        "fiscal_quarter": "Q1",
                        "metrics": ["net_income", "roe", "cet1_ratio"]
                    }
                }
            ]
        }
    )
    update_notes(
        subsection_id=main_subsection["id"],
        notes="Display as comparison table. Highlight top performer in each metric."
    )
    update_instructions(
        subsection_id=main_subsection["id"],
        instructions="Create a comparison table of key metrics for all Big 6 banks. Include net income, ROE, and CET1 ratio."
    )

    print("4. Configured subsection")

    # 5. Verify final state
    sections = get_sections(template["id"], include_content=True)
    print(f"5. Final template has {len(sections)} section(s)")
    for s in sections:
        print(f"   - {s['title']}: {len(s['subsections'])} subsections")
        for sub in s["subsections"]:
            config = sub.get("data_source_config")
            source = config["source_id"] if config else "none"
            print(f"     - position {sub['position']}: widget={sub['widget_type']}, source={source}")

    print("\n   [FULL WORKFLOW PASS]")
    return template["id"]


def cleanup_test_templates():
    """Clean up test templates."""
    from src.db import get_connection

    print("\n" + "="*60)
    print("CLEANUP: Removing test templates")
    print("="*60)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM templates
                WHERE created_by IN ('test_user', 'analyst')
                RETURNING id, name
            """)
            deleted = cur.fetchall()
            conn.commit()
            print(f"   Deleted {len(deleted)} test template(s)")
    finally:
        conn.close()


def main():
    print("\n" + "="*60)
    print("REPORT DESIGNER - WORKSPACE TOOLS TESTS")
    print("="*60)

    try:
        # Test data sources
        test_data_sources()

        # Test template CRUD
        template_id = test_template_crud()

        # Test section CRUD
        section_id, subsection_id = test_section_crud(template_id)

        # Test subsection operations
        test_subsection_operations(subsection_id)

        # Test full workflow
        test_full_workflow()

        print("\n" + "="*60)
        print("ALL TESTS PASSED")
        print("="*60)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # Cleanup
        cleanup_test_templates()


if __name__ == "__main__":
    main()
