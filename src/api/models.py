"""
Pydantic models for Report Designer API.

Request/response models for all API endpoints.
"""

from typing import Any, Literal, Optional
from pydantic import BaseModel


# ============================================================
# Literal Types (Enums)
# ============================================================

OutputFormat = Literal["pdf", "ppt"]
Orientation = Literal["landscape", "portrait"]
TemplateStatus = Literal["draft", "active", "archived"]
WidgetType = Literal["summary", "key_points", "table", "chart", "comparison", "custom"]
ContentType = Literal["text", "markdown", "html", "json"]
GeneratedBy = Literal["agent", "user_edit", "import"]
ChartType = Literal["bar", "line"]


# ============================================================
# Data Source Models
# ============================================================

class DataInputConfigRequest(BaseModel):
    """One data input used during subsection generation."""
    source_id: str
    method_id: str
    parameters: Optional[dict[str, Any]] = None


class ContextDependenciesRequest(BaseModel):
    """Optional context dependencies for generation ordering and context injection."""
    section_ids: Optional[list[str]] = None
    subsection_ids: Optional[list[str]] = None


class VisualizationConfigRequest(BaseModel):
    """Optional visualization configuration for chart/widget rendering."""
    chart_type: Optional[ChartType] = None
    title: Optional[str] = None
    x_key: Optional[str] = None
    y_key: Optional[str] = None
    series_key: Optional[str] = None
    metric_id: Optional[str] = None


class DataSourceConfigRequest(BaseModel):
    """Canonical generation config for a subsection."""
    inputs: list[DataInputConfigRequest]
    dependencies: Optional[ContextDependenciesRequest] = None
    visualization: Optional[VisualizationConfigRequest] = None


class DataSourceResponse(BaseModel):
    """Response model for data source registry entry."""
    id: str
    name: str
    description: str
    category: str
    retrieval_methods: Any  # JSONB - list of method definitions
    suggested_widgets: Optional[Any] = None  # JSONB
    is_active: bool
    created_at: Optional[str] = None


# ============================================================
# Template Models
# ============================================================

class TemplateCreateRequest(BaseModel):
    """Request model for creating a template."""
    name: str
    description: Optional[str] = None
    output_format: OutputFormat = "pdf"
    orientation: Orientation = "landscape"
    formatting_profile: Optional[dict[str, Any]] = None


class TemplateUpdateRequest(BaseModel):
    """Request model for updating a template."""
    name: Optional[str] = None
    description: Optional[str] = None
    output_format: Optional[OutputFormat] = None
    orientation: Optional[Orientation] = None
    status: Optional[TemplateStatus] = None
    formatting_profile: Optional[dict[str, Any]] = None


class TemplateResponse(BaseModel):
    """Response model for template."""
    id: str
    name: str
    description: Optional[str] = None
    created_by: str
    output_format: OutputFormat
    orientation: Optional[Orientation] = None
    status: TemplateStatus
    formatting_profile: Optional[dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_opened_at: Optional[str] = None


class TemplateSummary(BaseModel):
    """Summary model for template list item."""
    id: str
    name: str
    description: Optional[str] = None
    created_by: str
    output_format: OutputFormat
    status: TemplateStatus
    formatting_profile: Optional[dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SectionSummaryItem(BaseModel):
    """Summary of a section within template overview."""
    id: str
    position: int
    title: Optional[str] = None


class SectionsSummary(BaseModel):
    """Summary of all sections within template overview."""
    count: int
    sections: list[SectionSummaryItem]


class TemplateWithSections(BaseModel):
    """Template metadata with section summary."""
    template: TemplateResponse
    sections_summary: SectionsSummary


# ============================================================
# Subsection Models (embedded in section responses)
# ============================================================

class SubsectionSummary(BaseModel):
    """Summary of a subsection (without full content)."""
    id: str
    title: Optional[str] = None
    position: int
    widget_type: Optional[str] = None
    data_source_config: Optional[Any] = None  # JSONB
    has_notes: bool = False
    has_instructions: bool = False
    content_type: Optional[str] = None
    version_number: int = 0


class SubsectionWithContent(BaseModel):
    """Subsection with full content included."""
    id: str
    title: Optional[str] = None
    position: int
    widget_type: Optional[str] = None
    data_source_config: Optional[Any] = None
    has_notes: bool = False
    has_instructions: bool = False
    content_type: Optional[str] = None
    version_number: int = 0
    content: Optional[str] = None
    notes: Optional[str] = None
    instructions: Optional[str] = None


class SubsectionBasic(BaseModel):
    """Basic subsection info."""
    id: str
    title: Optional[str] = None
    position: int
    widget_type: Optional[str] = None
    data_source_config: Optional[Any] = None


# ============================================================
# Section Models
# ============================================================

class SectionCreateRequest(BaseModel):
    """Request model for creating a section."""
    title: Optional[str] = None
    position: Optional[int] = None  # None to append at end


class SectionUpdateRequest(BaseModel):
    """Request model for updating a section."""
    title: Optional[str] = None
    position: Optional[int] = None


class SectionResponse(BaseModel):
    """Response model for section with subsections."""
    id: str
    position: int
    title: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    subsections: list[dict[str, Any]]  # Flexible to handle various subsection formats


class SectionWithSubsections(BaseModel):
    """Section response after creation (with subsection info)."""
    id: str
    position: int
    title: Optional[str] = None
    created_at: Optional[str] = None
    subsections: list[SubsectionBasic]


class SectionFull(BaseModel):
    """Full section response including template_id."""
    id: str
    template_id: str
    position: int
    title: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    subsections: list[SubsectionBasic]


class SectionDeleteResponse(BaseModel):
    """Response for section deletion."""
    deleted: bool
    section_id: str


# ============================================================
# Subsection CRUD Models
# ============================================================

class SubsectionCreateRequest(BaseModel):
    """Request model for creating a subsection."""
    title: Optional[str] = None
    position: Optional[int] = None  # None to append at end


class SubsectionCreateResponse(BaseModel):
    """Response model for created subsection."""
    id: str
    section_id: str
    title: Optional[str] = None
    position: int
    widget_type: Optional[str] = None
    created_at: Optional[str] = None


class UpdateTitleRequest(BaseModel):
    """Request for updating subsection title."""
    title: str


class UpdateTitleResponse(BaseModel):
    """Response for title update."""
    id: str
    title: Optional[str] = None
    updated: bool


class ReorderSubsectionRequest(BaseModel):
    """Request for reordering a subsection."""
    new_position: int


class SubsectionDeleteResponse(BaseModel):
    """Response for subsection deletion."""
    deleted: bool
    subsection_id: str


# ============================================================
# Subsection Detail Models
# ============================================================

class VersionSummary(BaseModel):
    """Summary of a version in version history."""
    id: str
    version_number: int
    instructions: Optional[str] = None
    notes: Optional[str] = None
    content_preview: Optional[str] = None
    content_type: Optional[str] = None
    generated_by: Optional[str] = None
    is_final: bool = False
    created_at: Optional[str] = None


class SubsectionDetailResponse(BaseModel):
    """Full subsection detail with optional version history."""
    id: str
    section_id: str
    title: Optional[str] = None
    position: int
    widget_type: Optional[str] = None
    data_source_config: Optional[Any] = None
    notes: Optional[str] = None
    instructions: Optional[str] = None
    content: Optional[str] = None
    content_type: Optional[str] = None
    version_number: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    template_id: str
    section_title: Optional[str] = None
    versions: Optional[list[VersionSummary]] = None


# ============================================================
# Subsection Update Requests/Responses
# ============================================================

class UpdateNotesRequest(BaseModel):
    """Request for updating subsection notes."""
    notes: str
    append: bool = False


class UpdateNotesResponse(BaseModel):
    """Response for notes update."""
    id: str
    notes: Optional[str] = None
    updated: bool


class UpdateInstructionsRequest(BaseModel):
    """Request for updating subsection instructions."""
    instructions: str


class UpdateInstructionsResponse(BaseModel):
    """Response for instructions update."""
    id: str
    instructions: Optional[str] = None
    updated: bool


class ConfigureSubsectionRequest(BaseModel):
    """Request for configuring subsection data source."""
    widget_type: Optional[WidgetType] = None
    data_source_config: Optional[DataSourceConfigRequest] = None


class ConfigureSubsectionResponse(BaseModel):
    """Response for subsection configuration update."""
    id: str
    widget_type: Optional[str] = None
    data_source_config: Optional[Any] = None
    updated: bool


class SaveVersionRequest(BaseModel):
    """Request for saving a new subsection version."""
    content: str
    content_type: ContentType = "markdown"
    generated_by: GeneratedBy = "agent"
    is_final: bool = False
    generation_context: Optional[dict[str, Any]] = None
    title: Optional[str] = None


class SaveVersionResponse(BaseModel):
    """Response for version save."""
    version_id: str
    version_number: int
    subsection_id: str
    content_type: str
    generated_by: str
    is_final: bool
    title: Optional[str] = None
    created_at: Optional[str] = None


# ============================================================
# Chat Models
# ============================================================

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    focus_section_id: Optional[str] = None
    focus_subsection_id: Optional[str] = None


class ToolCallLog(BaseModel):
    """Log entry for a tool call."""
    tool: str
    args: dict[str, Any]
    raw_args: Optional[dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    tool_calls: list[ToolCallLog]
    conversation_id: str


class MessageResponse(BaseModel):
    """Response model for a conversation message."""
    id: str
    role: str
    content: str
    surface: str
    section_id: Optional[str] = None
    subsection_id: Optional[str] = None
    sequence_number: int
    created_at: Optional[str] = None


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history."""
    conversation_id: str
    messages: list[MessageResponse]


# ============================================================
# Generation Models
# ============================================================

class StartGenerationRequest(BaseModel):
    """Request model for starting template generation."""
    run_inputs: Optional[dict[str, Any]] = None


class GenerationRequiredInput(BaseModel):
    """Single run input required to resolve template variables."""
    key: str
    label: str
    type: str
    options: Optional[list[Any]] = None
    used_by: list[dict[str, Any]]


class GenerationRequirementsResponse(BaseModel):
    """Response model for generation requirements scan."""
    ready: bool
    required_inputs: list[GenerationRequiredInput]
    blocking_errors: list[dict[str, Any]]
    subsections_considered: int
    saved_run_inputs: dict[str, Any] = {}


# ============================================================
# Template Version Models
# ============================================================

class CreateTemplateVersionRequest(BaseModel):
    """Request for creating a template version snapshot."""
    name: Optional[str] = None


class TemplateVersionSummary(BaseModel):
    """Summary of a template version."""
    id: str
    template_id: str
    version_number: int
    name: str
    created_by: Optional[str] = None
    created_at: Optional[str] = None


class TemplateVersionResponse(BaseModel):
    """Full template version with snapshot."""
    id: str
    template_id: str
    version_number: int
    name: str
    snapshot: Any  # JSONB snapshot of template state
    created_by: Optional[str] = None
    created_at: Optional[str] = None


class RestoreVersionResponse(BaseModel):
    """Response for restoring a template version."""
    success: bool
    template_id: str
    restored_from: str
    sections_restored: int


class ForkTemplateRequest(BaseModel):
    """Request for forking a template."""
    new_name: str


class ForkTemplateResponse(BaseModel):
    """Response for template fork."""
    id: str
    name: str
    description: Optional[str] = None
    created_by: str
    output_format: OutputFormat
    orientation: Optional[Orientation] = None
    status: TemplateStatus
    formatting_profile: Optional[dict[str, Any]] = None
    created_at: Optional[str] = None
    forked_from: str


class SetSharedRequest(BaseModel):
    """Request for setting template shared status."""
    is_shared: bool
