# TODO - Report Designer

> See `docs/README_CONCEPT.md` for full product vision
> See `docs/BUILD_ROADMAP.md` for phased implementation plan

---

## Data Layer (Complete)

- [x] Define table schemas (`schemas/*.sql`)
- [x] Define 25 financial metrics (`scripts/database/metrics.py`)
- [x] Create mock data for all 6 banks (5 quarters: FY2024 Q1-Q4, FY2025 Q1)
- [x] Build data generation script (`scripts/database/generate_mock_data.py`)
- [x] Build data ingestion script (`scripts/database/load_data.py`)
- [x] Load data into Postgres

### Data Summary
```
transcripts:    60 records (6 banks × 2 sections × 5 quarters)
financials:    750 records (6 banks × 25 metrics × 5 quarters)
stock_prices:   30 records (6 banks × 5 quarters)

Periods: 2024 Q1, 2024 Q2, 2024 Q3, 2024 Q4, 2025 Q1
```

### Database Scripts
```bash
# Generate fresh mock data
python scripts/database/generate_mock_data.py

# Load data into Postgres
python scripts/database/load_data.py
```

---

## MCP Data Retrievers (Complete)

- [x] `src/retrievers/transcripts.py` - search_transcripts tool
- [x] `src/retrievers/financials.py` - search_financials tool
- [x] `src/retrievers/stock_prices.py` - search_stock_prices tool
- [x] `src/mcp_server.py` - MCP server exposing all tools
- [x] `scripts/test/test_retrievers.py` - Test script for retrievers

| Tool | Description |
|------|-------------|
| `search_transcripts` | Earnings call transcripts (management discussion / Q&A) |
| `search_financials` | 25 financial metrics (profitability, capital, credit, etc.) |
| `search_stock_prices` | Stock prices with QoQ/YoY changes |

---

## Workspace Schema (Complete)

- [x] `schemas/workspace/templates.sql` - Workspace containers
- [x] `schemas/workspace/conversations.sql` - Persistent chat history
- [x] `schemas/workspace/sections.sql` - Ordered pages/slides
- [x] `schemas/workspace/subsections.sql` - Content areas with notes/instructions
- [x] `schemas/workspace/subsection_versions.sql` - Version history
- [x] `schemas/workspace/data_source_registry.sql` - Available data sources
- [x] `schemas/workspace/layouts.sql` - Pre-built layout definitions (5 layouts)
- [x] `scripts/database/seed_registry.py` - Seed registry with 3 data sources

### Database Tables
```
templates              → Workspace container (name, format, orientation)
conversations/messages → Persistent chat history
sections               → Ordered pages/slides
subsections            → Content areas (notes, instructions, content)
subsection_versions    → Iteration history
data_source_registry   → Available data sources (transcripts, financials, stock_prices)
layouts                → Pre-built layouts (single_content, two_column, etc.)
```

---

## MCP Workspace Tools (Complete)

- [x] `src/workspace/templates.py` - Template CRUD
- [x] `src/workspace/sections.py` - Section CRUD
- [x] `src/workspace/subsections.py` - Subsection ops, notes, instructions, versioning
- [x] `src/workspace/data_sources.py` - Data source registry queries
- [x] `scripts/test/test_workspace.py` - Full test suite

### All MCP Tools (16 total)

**Data Retrieval (3):**
| Tool | Description |
|------|-------------|
| `search_transcripts` | Earnings call transcripts |
| `search_financials` | 25 financial metrics |
| `search_stock_prices` | Stock prices with changes |

**Templates (4):**
| Tool | Description |
|------|-------------|
| `get_template` | Get workspace overview |
| `create_template` | Create new workspace |
| `update_template` | Update properties |
| `list_templates` | List with filters |

**Sections (4):**
| Tool | Description |
|------|-------------|
| `get_sections` | Get sections with subsections |
| `create_section` | Create with layout |
| `update_section` | Update properties |
| `delete_section` | Delete with cascade |

**Subsections (5):**
| Tool | Description |
|------|-------------|
| `get_subsection` | Get details + versions |
| `update_notes` | Update collaboration notes |
| `update_instructions` | Update generation prompt |
| `configure_subsection` | Set data source + widget |
| `save_subsection_version` | Save content version |

**Registry (1):**
| Tool | Description |
|------|-------------|
| `get_data_sources` | Available data sources |

### Running Tests
```bash
# Test data retrievers
python scripts/test/test_retrievers.py

# Test workspace tools
python scripts/test/test_workspace.py

# Start MCP server (all 16 tools)
python -m src.mcp_server
```

---

## Next: Backend API + Simple UI

- [ ] FastAPI skeleton with endpoints
- [ ] Chat endpoint (send message → agent response)
- [ ] Template/section state endpoints
- [ ] Simple React UI with:
  - Template list
  - Chat panel
  - Section view
  - Content preview

---

## Future Phases

See `docs/BUILD_ROADMAP.md` for:
- Visual Designer (layout picker, drag/drop)
- File uploads and processing
- PDF/PPT generation
- Template versioning and sharing
- Mini popups and polish

---

## Decisions Made

1. **Transcript sections:** Just management_discussion and qa (no further breakdown)
2. **Financial metrics:** Top 25 shared across all banks (defined in `scripts/database/metrics.py`)
3. **No embeddings for bank data:** Retrieving full sections, no semantic search needed
4. **Mock data approach:** Semi-realistic mock data to build framework; replace with real pipelines later
5. **Notes vs Instructions:** Notes = informal context, Instructions = formal generation prompts
6. **Templates are living workspaces:** Contain conversation, sections, version history
7. **UUID primary keys:** Client-side generation, merge-friendly
8. **JSONB for data_source_config:** Flexible, supports varying retrieval methods
9. **Separate version table:** Efficient queries, pagination support
