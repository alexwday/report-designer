# Report Designer

An LLM-powered document generation agent that enables RBC Finance employees to create, customize, and regenerate data-driven reports through a conversational interface.

## Table of Contents

- [Overview](#overview)
- [Core Concepts](#core-concepts)
- [Architecture](#architecture)
- [Document Structure](#document-structure)
- [The Agent](#the-agent)
- [Conversation Model](#conversation-model)
- [User Interface](#user-interface)
- [Data Sources](#data-sources)
- [Section Building Workflow](#section-building-workflow)
- [Templates](#templates)
- [Generation Pipeline](#generation-pipeline)
- [Access Model](#access-model)
- [Technical Stack](#technical-stack)
- [Future Considerations](#future-considerations)

---

## Overview

Report Designer is an internal application that combines an intelligent LLM agent with an intuitive visual interface to streamline the creation of structured reports and presentations. Users interact with the agent through a chat interface while designing documents visually, specifying how each component should be generated from available data sources.

The system produces both the final report output (PDF or PowerPoint) and maintains a reusable template workspace that can regenerate updated reports with refreshed data in subsequent periods (e.g., quarterly reports).

---

## Core Concepts

### Template = Living Workspace

A template is not just a configuration file—it's a complete, persistent workspace that contains:

- **Full conversation history** (never ends, always resumable)
- **All sections** with their complete version history
- **Uploaded files** (both raw and processed)
- **Generated outputs** (all PDFs/PPTs ever generated from this template)
- **Version snapshots** (user-saved checkpoints of the entire template state)

When a user opens a template, they can immediately continue the conversation with the agent from where they left off.

### Reports vs Templates

| Reports | Templates |
|---------|-----------|
| Final output documents (PDF/PPT) | The workspace that generates reports |
| Contains rendered data and content | Contains instructions for generating content |
| Static snapshot of a point in time | Living, evolving, reusable |
| Multiple reports saved per template | One template produces many reports |

---

## Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         React Frontend                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ Visual Report│ │  Chat Popup  │ │   Template   │            │
│  │   Designer   │ │  (Main +     │ │   Manager    │            │
│  │              │ │   Mini)      │ │              │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │Layout Picker │ │ Data Source  │ │   Notes &    │            │
│  │ (Drag/Drop)  │ │   Widgets    │ │ Instructions │            │
│  └──────────────┘ └──────────────┘ │   Sidebar    │            │
│                                     └──────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ Agent Engine │ │ Data Source  │ │   Report     │            │
│  │  (LLM Core)  │ │  Registry    │ │  Generator   │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │    File      │ │   Template   │ │    Chart     │            │
│  │  Processor   │ │   Manager    │ │   Builder    │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         PostgreSQL                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │   Internal   │ │  Templates   │ │ Conversations│            │
│  │   Datasets   │ │  & Sections  │ │   & Files    │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Document Structure

### Hierarchy

```
Report
├── Section 1 (= Page 1 of PDF / Slide 1 of PPT)
│   └── Layout: Selected from available options
│       ├── Subsection A → Data source + Instructions + Widget type
│       ├── Subsection B → Data source + Instructions + Widget type
│       └── Subsection C → Data source + Instructions + Widget type
│
├── Section 2 (= Page 2 / Slide 2)
│   └── Layout: "Full Page Table"
│       └── Subsection → Data source + Instructions + Widget type
│
├── Section 3 (= Page 3 / Slide 3)
│   └── Layout: "Header + Chart + Commentary"
│       ├── Subsection: Header
│       ├── Subsection: Chart
│       └── Subsection: Commentary
│
└── ... more sections
```

### Terminology

| Term | Definition |
|------|------------|
| **Section** | One page (PDF) or slide (PowerPoint). The top-level building block. |
| **Layout** | A pre-built arrangement of subsections with defined positions, sizes, and styling. Similar to PowerPoint slide layouts. Users select from available layouts—they cannot create custom arrangements. |
| **Subsection** | A content area within a layout. This is where data sources are linked and content is generated. |
| **Widget** | The content type for a subsection (summary, table, chart, key points, custom text, etc.) |

### Output Formats

- **PDF**: Page-based format, styled like presentation slides. Supports landscape or portrait orientation.
- **PowerPoint**: Native .pptx format for further editing or presentation.

---

## The Agent

The agent is the central intelligence of the system. It serves as the complete system link—understanding how everything works and guiding users through the entire process.

### Agent Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Guide** | Walks users through report creation step-by-step |
| **Suggest** | Recommends data sources, retrieval methods, and content approaches based on user descriptions |
| **Fill in** | Can proactively fill in details and make reasonable suggestions |
| **Clarify** | Asks questions when requirements are ambiguous |
| **Confirm** | Engages in back-and-forth dialogue before finalizing decisions |
| **Generate** | Creates the actual content for each subsection |
| **Review** | Can autonomously review and suggest edits to previously generated sections |
| **Remember** | Maintains notes about user preferences and decisions |

### Agent Context

On every message, the agent receives:

1. **Full conversation history** (persistent across sessions)
2. **All sections** with current state (instructions, notes, content, versions)
3. **Data source registry** (all available sources and their retrieval methods)
4. **Current UI state** (which section/subsection the user is viewing)
5. **Template metadata** (layout, orientation, version info)

This comprehensive context enables cross-section awareness and coherent document generation.

---

## Conversation Model

### Conversation Persistence

- The complete conversation is stored in PostgreSQL
- The full conversation history is sent with each subsequent message to the agent
- Conversations never explicitly "end"—users can always reopen a template and continue
- All interactions (main chat, mini popups, agent actions) feed into the same conversation

### Multi-Surface Conversation

The conversation manifests across multiple UI surfaces:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Unified Conversation                         │
│                    (stored in Postgres)                         │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Main Chat     │   Mini Popups   │   Agent Actions/Notes       │
│   Popup         │   (Contextual)  │   (System-generated)        │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ User-initiated  │ Agent-initiated │ Background reasoning        │
│ full dialogue   │ questions while │ and observations            │
│                 │ user works      │                             │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

- **Main Chat Popup**: Accessible from anywhere in the app. For extended dialogue and complex requests.
- **Mini Popups**: Appear contextually within the visual designer. Agent asks quick questions or makes comments as the user works.
- **Agent Notes**: The agent's internal observations and reasoning, visible to users in the sidebar.

---

## User Interface

### Primary Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Header / Toolbar                                               │
├───────────────┬─────────────────────────────────┬───────────────┤
│               │                                 │               │
│   Section     │      Visual Document            │    Notes &    │
│   Navigator   │         Preview                 │  Instructions │
│               │                                 │    Sidebar    │
│               │    (Main workspace area)        │               │
│               │                                 │               │
│               │    ┌─────────────────────┐      │               │
│               │    │   Mini popup from   │      │               │
│               │    │   agent appears     │      │               │
│               │    │   contextually      │      │               │
│               │    └─────────────────────┘      │               │
│               │                                 │               │
├───────────────┴─────────────────────────────────┴───────────────┤
│  [💬 Chat]  ← Floating button to open main chat popup           │
└─────────────────────────────────────────────────────────────────┘
```

### Key UI Components

| Component | Purpose |
|-----------|---------|
| **Visual Document Preview** | Main workspace showing the report as it will appear. WYSIWYG editing. |
| **Layout Picker** | Drag-and-drop selection of pre-built layouts for new sections |
| **Data Source Widgets** | UI for selecting and configuring data sources for each subsection |
| **Notes & Instructions Sidebar** | Shows and allows editing of notes (collaboration context) and instructions (generation prompts) |
| **Main Chat Popup** | Full conversation interface, accessible from anywhere |
| **Mini Popups** | Contextual agent interactions within the visual designer |
| **Section Navigator** | Quick navigation between sections/pages |

### Layout Selection

Users select from pre-built layouts—they cannot create arbitrary arrangements:

```
┌─────────────────────────────────────────────────────────────────┐
│  Select a Layout                                                │
│                                                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │  Title  │  │ 2-Column│  │  Chart  │  │  Table  │   ...      │
│  │  Only   │  │         │  │ + Text  │  │  Full   │            │
│  │         │  │  ┌─┬─┐  │  │  ┌───┐  │  │ ┌─────┐ │            │
│  │ ┌─────┐ │  │  │ │ │  │  │  │   │  │  │ │     │ │            │
│  │ │     │ │  │  │ │ │  │  │  ├───┤  │  │ ├─────┤ │            │
│  │ └─────┘ │  │  └─┴─┘  │  │  │   │  │  │ │     │ │            │
│  └─────────┘  └─────────┘  │  └───┘  │  │ └─────┘ │            │
│                            └─────────┘  └─────────┘            │
│                                                                 │
│  Layouts define: positions, sizes, fonts, styling              │
└─────────────────────────────────────────────────────────────────┘
```

Layouts define:
- Number and arrangement of subsections
- Position and size of each subsection area
- Font styles, colors, spacing
- Orientation compatibility (landscape/portrait)

---

## Data Sources

### Source Types

#### 1. Database Sources (Postgres)

Pre-structured internal datasets managed by the data team, including:
- Hierarchy mappings
- Financial tables and line items
- Reference data and lookups
- Documentation and text content

Each database source includes:
- **Retrieval methods**: Defined ways to query the data
- **Parameters**: Inputs needed (typically quarter, year)
- **Metadata**: Descriptions for the agent to understand appropriate usage

#### 2. Ad-hoc Uploads

User-uploaded files for one-time or recurring use:

| Format | Processing |
|--------|------------|
| PDF (.pdf) | Extract text, chunk, embed for similarity search |
| Word (.docx) | Extract text, chunk, embed for similarity search |
| PowerPoint (.ppt, .pptx) | Extract slide text/content, chunk, embed |
| Excel (.xlsx) | Parse sheets into structured tables |
| Text (.txt) | Chunk, embed for similarity search |

**Processing happens immediately on upload** so users can work with the content right away.

### Data Source Registry

The data team maintains a registry of all available sources:

```python
# Conceptual structure
{
    "source_id": "credit_risk_quarterly",
    "name": "Credit Risk Quarterly Reports",
    "description": "Quarterly credit risk assessments by business line",
    "retrieval_methods": [
        {
            "method_id": "by_quarter",
            "description": "Get full report for a specific quarter",
            "parameters": [
                {
                    "key": "year",
                    "type": "int",
                    "prompt": "Which year?"
                },
                {
                    "key": "quarter",
                    "type": "enum",
                    "options": ["Q1", "Q2", "Q3", "Q4"],
                    "prompt": "Which quarter?"
                }
            ],
            "returns": "Full quarterly risk report document"
        },
        {
            "method_id": "trend",
            "description": "Get trend data across multiple quarters",
            "parameters": [
                {
                    "key": "year",
                    "type": "int",
                    "prompt": "Ending year?"
                },
                {
                    "key": "num_quarters",
                    "type": "int",
                    "prompt": "How many quarters back?"
                }
            ],
            "returns": "Trend data with quarter-over-quarter comparisons"
        }
    ],
    "suggested_for": ["summaries", "key points", "trend tables"]
}
```

The agent uses this registry to:
1. Explain available sources to users
2. Suggest appropriate retrieval methods based on user descriptions
3. Know what parameters to collect for template configuration

---

## Section Building Workflow

### Step-by-Step Process

```
1. User creates a new section
         │
         ▼
2. User selects a layout (drag and drop)
         │
         ▼
3. For each subsection in the layout:
         │
         ├─► User selects data source via widget
         │
         ├─► User describes what they want
         │
         ├─► Agent suggests retrieval method
         │
         ├─► Agent generates preview content
         │         │
         │         ▼
         │   User reviews
         │         │
         │         ├─► Not happy? Refine instructions
         │         │         │
         │         │         └─► Agent generates new version
         │         │                    │
         │         │                    └─► (repeat until satisfied)
         │         │
         │         └─► Happy? Lock in final version
         │
         └─► Move to next subsection

4. Section complete, move to next section
```

### Version Control

Each subsection maintains a version history:

```
Subsection
├── version_1 (content, instructions, notes)
├── version_2 (content, instructions, notes)
├── version_3 (content, instructions, notes) ◄── current working
└── final_version ───► used for template
```

- Every iteration is saved as a version
- Users can undo/redo through versions
- When satisfied, the current version becomes the final
- Final version is self-contained (no need to replay iteration history)

### Notes vs Instructions

Both are editable by the user AND the agent:

| Notes | Instructions |
|-------|--------------|
| Collaboration context and reasoning | Formal generation prompt |
| "User prefers executive-friendly tone" | "Summarize top 5 risks in 3 bullet points" |
| "Tried table format, user preferred bullets" | "Format as bullet list, not table" |
| "User mentioned comparing to Q1" | "Include comparison to previous quarter" |
| Informal, captures the journey | Formal, used for generation |

### Widget Types

**Pre-built widgets** (structured output):
- Summary
- Key Points / Bullets
- Table
- Chart / Graph (database-specific generation)
- Image
- Comparison
- Trend Analysis

**Custom widget**:
- User describes what they want in free-form text
- Agent generates text/markdown content
- Limited to what the LLM can produce (text-based output)

### Charts and Graphs

Chart generation is **database-specific**, not LLM-configured:
- Each database source knows what chart types it supports
- The system has pre-built chart generation logic per source
- Users select chart type from available options for that data source
- More reliable than asking the LLM to generate chart configurations

---

## Templates

### Template Contents

A complete template workspace includes:

```
Template
├── Metadata
│   ├── template_id
│   ├── name
│   ├── created_by
│   ├── created_at
│   └── layout settings (orientation, preset)
│
├── Conversation
│   └── Full message history (never ends)
│
├── Sections[]
│   └── For each section:
│       ├── section_id
│       ├── order
│       ├── layout_id
│       └── Subsections[]
│           └── For each subsection:
│               ├── subsection_id
│               ├── data_source configuration
│               ├── instructions (final)
│               ├── notes
│               ├── widget_type
│               ├── version_history[]
│               └── current_content
│
├── Uploaded Files[]
│   ├── Raw files
│   └── Processed versions
│
├── Generated Outputs[]
│   └── All PDFs/PPTs ever generated
│       ├── Q1_2025_output.pdf
│       ├── Q2_2025_output.pdf
│       └── ...
│
└── Version Snapshots[]
    ├── v1.0 (complete state at save time)
    ├── v2.0 (complete state at save time)
    └── ...
```

### Template Versioning

Users can explicitly save a version snapshot of the entire template:

```
Working State (current)
     │
     ├── User clicks "Save as Version"
     │
     ▼
v2.0 Snapshot Created
     │
     └── Immutable record of:
         • Conversation at that point
         • All sections and their states
         • All files
         • All settings
```

Users continue working in the current state. Versions are immutable reference points they can return to.

### Sharing Model

Sharing works as **branching/forking**, not real-time collaboration:

```
User A's Template (v2.0)
        │
        ├──── Share ────► User B receives a copy (fork)
        │                       │
        ▼                       ▼
User A continues              User B has independent copy
their own changes             Makes their own changes
```

- No real-time collaborative editing
- Each user works on their own copy
- Clean, no conflict resolution needed

### Loading a Template

When a user loads an existing template to generate a new report:

```
1. User opens template
         │
         ▼
2. System scans all sections for parameters needing input
   (quarter, year, file uploads, etc.)
         │
         ▼
3. Agent asks collected questions in sequence or grouped:
   • "Which year?" → 2025
   • "Which quarter?" → Q2
   • "Please upload the latest market analysis PDF" → [file]
         │
         ▼
4. All data sources now have resolved parameters
         │
         ▼
5. Agent offers options:
   • "Ready to generate full report?"
   • "Want to review any sections first?"
   • "Any changes to make before generating?"
         │
         ▼
6. Generate report (or review section by section)
```

Even during regeneration, the agent may ask confirmation questions for sections with ambiguous or changed data.

---

## Generation Pipeline

### Sequential Generation with Context

```
Section 1
    │
    ├─► Generate all subsections
    │
    ├─► Output added to context
    │
    ▼
Section 2
    │
    ├─► Generate with Section 1 in context
    │
    ├─► Output added to context
    │
    ▼
Section 3
    │
    ├─► Generate with Sections 1-2 in context
    │
    ├─► Output added to context
    │
    ▼
... continue for all sections ...
    │
    ▼
Agent Review Pass
    │
    ├─► Reviews full report for coherence
    │
    ├─► Checks cross-references
    │
    ├─► Identifies inconsistencies
    │
    ▼
Issues Found?
    │
    ├─► Yes: Agent suggests edits or autonomously fixes
    │         (user can intervene or approve)
    │
    └─► No: Finalize and render output
```

### Key Pipeline Features

- **Context accumulation**: Each section generated with all previous sections as context
- **Cross-section awareness**: Agent can reference and maintain consistency across sections
- **Autonomous editing**: Agent can loop back to fix issues discovered during review
- **Multi-pass**: Multiple generation and review passes are acceptable
- **User intervention**: Users can pause and adjust at any point

---

## Access Model

### User Access

Report Designer is an internal application for RBC Finance employees with open access:

- All users can view all available shared data sources
- All users can upload their own documents
- All users can create reports and templates
- All users can save and share templates (fork model)

### Data Team Responsibilities

A separate data team manages the shared infrastructure:

| Data Team Manages | End Users Consume |
|-------------------|-------------------|
| Add/configure data sources | Use available sources |
| Define retrieval methods | Build reports with sources |
| Create and maintain preset layouts | Select from available layouts |
| Publish base templates | Fork and customize templates |
| System updates and maintenance | Create personal templates |

```
┌────────────────────────┐     ┌────────────────────────┐
│      Data Team         │     │      End Users         │
├────────────────────────┤     ├────────────────────────┤
│ • Add data sources     │     │ • Use available sources│
│ • Configure retrieval  │────►│ • Build reports        │
│   methods              │     │ • Save templates       │
│ • Create layouts       │     │ • Share (fork) with    │
│ • Publish updates      │     │   colleagues           │
└────────────────────────┘     └────────────────────────┘
```

---

## Technical Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React |
| **Backend** | Python, FastAPI |
| **Database** | PostgreSQL |
| **LLM** | TBD (to be selected) |
| **PDF Generation** | TBD |
| **PPT Generation** | TBD |

---

## Future Considerations

Areas requiring further design and implementation decisions:

### Technical Decisions
- LLM provider and model selection
- PDF rendering engine
- PowerPoint generation library
- File processing pipeline details
- Embedding model for similarity search
- Context management strategy for long conversations

### Product Decisions
- Specific preset layout designs
- Default template library (starter templates from data team)
- Notification system for ad-hoc upload reminders
- Search/discovery for shared templates
- Template categorization and tagging

### Scale Considerations
- Conversation history summarization for very long histories
- Caching strategies for frequently accessed data
- Concurrent generation for independent sections
- Storage strategy for generated outputs

---

## Development Status

This document represents the conceptual design phase. No implementation has begun. This README should be updated as design decisions are refined and implementation progresses.

---

## Session Notes

*This section captures key decisions from the initial design session for future reference.*

### Key Design Decisions Made

1. **Template = Living Workspace**: Not just config, but complete persistent state including conversation
2. **Section = Page/Slide**: Clean 1:1 mapping for document structure
3. **Layouts are Fixed**: Users select from pre-built options, no custom arrangements
4. **Conversation Never Ends**: Persistent, resumable, full context always available
5. **Branching for Sharing**: Fork model, no real-time collaboration
6. **Charts are Database-Specific**: Pre-built logic per source, not LLM-configured
7. **Immediate File Processing**: Ad-hoc uploads processed on upload, not on-demand
8. **Sequential Generation with Context**: Each section builds on previous for coherence
9. **Agent Autonomy with User Control**: Agent can suggest and auto-fix, user can intervene
10. **Dual-Surface Conversation**: Main popup + contextual mini-popups, same underlying conversation
