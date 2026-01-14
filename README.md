# Report Designer

An LLM-powered document generation agent that enables RBC Finance employees to create, customize, and regenerate data-driven reports through a conversational interface.

## Overview

Report Designer is an internal application that combines an intelligent agent with an intuitive UI to streamline the creation of structured reports and presentations. Users interact with the agent through a chat interface to design documents section-by-section, specifying how each component should be generated from available data sources. The system produces both the final report output and a reusable template that can regenerate updated reports with refreshed data in subsequent periods.

## Core Concepts

### The Agent

The agent serves as the central orchestrator of the entire system. It:

- **Guides users** through the report creation process step-by-step
- **Understands context** about available data sources, layout options, and output formats
- **Suggests content** and fills in details based on user intent
- **Asks clarifying questions** when requirements are ambiguous
- **Confirms decisions** through back-and-forth conversation before finalizing
- **Translates requests** into the appropriate backend operations
- **Generates outputs** including both the final report and reusable template

The agent maintains an ongoing dialogue with users, ensuring alignment at each step rather than making assumptions silently.

### Reports vs Templates

**Reports** are the final output documents containing actual data and content, rendered as PDF (page-based, slide-like format) or PowerPoint presentations.

**Templates** are reusable specifications that define:
- The document structure (sections, subsections, layouts)
- Data source mappings for each content block
- Generation instructions (summarize, extract key points, create table, etc.)
- Data refresh parameters (quarter, year, or other selection criteria)
- Notifications for sections requiring manual ad-hoc data uploads

When a user regenerates a report from a template, the agent may still ask confirmation questions to handle any changes in data availability or to verify assumptions for the new reporting period.

## User Workflow

### 1. Layout Selection

Users begin by either:
- Selecting a **preset layout** (e.g., executive summary, quarterly review, financial analysis)
- Creating a **custom layout** from scratch

Layouts define the overall document structure and orientation (landscape or portrait).

### 2. Section Design

For each section or subsection, users specify:
- **Content type**: narrative text, summary, key points, tables, charts, images
- **Data source**: which dataset(s) to pull from
- **Generation instructions**: how the agent should process and present the data

The agent assists throughout this process, suggesting appropriate content types based on the selected data and asking questions to clarify intent.

### 3. Data Source Configuration

Users configure how data should be retrieved:
- **Structured data**: Select from pre-configured Postgres datasets by specifying parameters like quarter and year
- **Ad-hoc uploads**: Upload documents (docx, pdf, ppt, txt, xlsx) for one-time or recurring use

Each data source has a defined retrieval method that the template will use for future regeneration.

### 4. Review and Generation

Before generating, the agent walks through a confirmation process:
- Reviews the complete document structure
- Confirms data source selections and parameters
- Validates generation instructions for each section
- Allows final adjustments

The system then generates both the report output and the template specification.

### 5. Template Reuse

When regenerating from a saved template:
- User selects the template and specifies new data parameters (e.g., Q2 2025 instead of Q1 2025)
- Agent notifies user of any sections requiring ad-hoc data uploads
- Agent may ask confirmation questions for sections with ambiguous or changed data
- System generates the updated report

## Data Sources

### Postgres Datasets

Pre-structured internal datasets available through the system include:
- **Hierarchy mappings**: Organizational and categorical structures
- **Financial tables**: Line items, accounts, metrics
- **Reference data**: Lookups, classifications, metadata
- **Documentation**: Policy documents, procedures, guidelines

Each dataset is configured with:
- A retrieval method tied to temporal parameters (quarter, year)
- Schema information for the agent to understand available fields
- Descriptions to help the agent suggest appropriate usage

### User Uploads

Users can upload documents in the following formats:
- Microsoft Word (.docx)
- PDF (.pdf)
- PowerPoint (.ppt, .pptx)
- Plain text (.txt)
- Excel (.xlsx)

Uploaded documents can be used as data sources for content generation (summarization, extraction, analysis) within report sections.

## Output Formats

### PDF (Page-Based)

PDF output follows a slide-like, page-based format similar to PowerPoint:
- Each page represents a distinct section or content block
- Supports both landscape and portrait orientations
- Optimized for presentation and printing

### PowerPoint

Native PowerPoint output for users who need to further edit or present the content in slide format.

## Technical Architecture

### Backend
- **Language**: Python
- **Framework**: FastAPI
- **Database**: PostgreSQL

### Frontend
- **Framework**: React

### Key Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         React Frontend                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Chat Interface │  │  Layout Builder │  │ Template Manager│  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Agent Engine  │  │  Data Services  │  │ Report Generator│  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         PostgreSQL                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Internal Datasets│  │    Templates    │  │  User Uploads   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Access Model

Report Designer is an internal application for RBC Finance employees with open access:
- All users can view all available datasets
- All users can upload their own documents
- All users can create reports and templates
- Templates are shareable across all users

## Future Considerations

This document represents the initial concept. Implementation details for the following areas will be defined as development progresses:

- LLM provider and model selection
- Template storage format and versioning
- Specific preset layout designs
- Data source registration and management interface
- Document processing pipeline for uploads
- PDF/PowerPoint rendering engine selection
