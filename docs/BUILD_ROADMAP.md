# Report Designer - Build Roadmap

## Component Dependencies

```
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │  Schema/Models  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
     │ Data Source │  │  Template   │  │    File     │
     │  Registry   │  │   CRUD      │  │  Processor  │
     └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
            │                │                │
            └────────────────┼────────────────┘
                             ▼
                    ┌─────────────────┐
                    │  Agent Engine   │
                    │  (LLM + Context)│
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
     │    Chat     │  │   Visual    │  │   Report    │
     │  Interface  │  │  Designer   │  │  Generator  │
     └─────────────┘  └─────────────┘  └─────────────┘
```

## Recommended Approach: Hybrid (Vertical Slice + Solid Foundation)

Start with a vertical slice to validate the concept, but design foundations properly from the start.

---

## Phase 1: Foundations + Minimal Slice

**Goal**: User can chat with agent, describe a summary, see it generated, export basic PDF

### Database Schema
- Templates, sections, subsections, conversations
- Data source registry structure
- File metadata (not processing yet)

### Backend Skeleton
- FastAPI project structure
- Basic models and endpoints
- One mock data source with one retrieval method

### Agent MVP
- Basic LLM integration (pick a provider)
- Simple context: conversation + current section
- Generate text content for one widget type (summary)

### Frontend Skeleton
- React project structure
- Basic template list view
- Simple chat interface (main popup only)
- Hardcoded single layout preview

### Output MVP
- Generate simple PDF (even just HTML→PDF initially)

---

## Phase 2: Core Workflows

**Goal**: User can build multi-section report with real data, iterate on content

### Data Sources
- Data source registry (CRUD)
- 2-3 real Postgres data sources
- Basic file upload (start with XLSX → tables)
- Retrieval method execution

### Section Building
- Multiple widget types (summary, table, key points)
- Version history for subsections
- Notes and instructions (editable)

### Visual Designer V1
- Layout picker (3-4 layouts)
- Section navigator
- Preview that updates as you build

### Agent Enhancements
- Full context (all sections, registry)
- Retrieval method suggestions
- Iterative refinement loop

---

## Phase 3: Template System

**Goal**: User can save template, share it, others can fork and use it

### Template Persistence
- Save complete template state
- Load and resume
- Parameter prompts on load (quarter, year)

### Template Versioning
- Save version snapshots
- Restore from version

### Sharing
- Fork/copy mechanism
- Template browser

---

## Phase 4: Full File Processing

**Goal**: User can upload PDFs and reference them in report sections

### Upload Pipeline
- PDF processing (extract, chunk, embed)
- DOCX processing
- PPT processing
- Similarity search integration

### Agent Integration
- Query uploaded documents
- Reference in generation

---

## Phase 5: Advanced Generation

**Goal**: Full generation pipeline with cross-section coherence

### Sequential Pipeline
- Section-by-section with context accumulation
- Agent review pass
- Autonomous edit suggestions

### Output Polish
- Proper PDF styling matching layouts
- PowerPoint generation
- Orientation support

---

## Phase 6: UI Polish & Mini Popups

**Goal**: Polished user experience

### Chat Experience
- Mini popups in visual designer
- Notes/instructions sidebar
- Smooth conversation flow

### Visual Designer Polish
- Drag and drop refinement
- Real-time preview updates
- Better layout selection UX

---

## Technical Decisions Needed Before Building

| Decision | Options to Consider |
|----------|---------------------|
| **LLM Provider** | Claude API, OpenAI GPT, Azure OpenAI, Self-hosted |
| **PDF Library** | WeasyPrint, ReportLab, Puppeteer/Playwright |
| **PPT Library** | python-pptx |
| **Embedding Model** | OpenAI embeddings, Sentence Transformers, Cohere |
| **File Storage** | Local filesystem, S3/MinIO, Azure Blob |
| **Vector Store** | pgvector (Postgres), Pinecone, Weaviate, ChromaDB |

---

## Notes

- Each phase builds on the previous
- Phases are estimated at roughly 1-2 weeks each depending on team size
- The vertical slice in Phase 1 is critical for validating the core concept early
- Technical decisions (LLM, PDF library, etc.) should be made before Phase 1 begins
