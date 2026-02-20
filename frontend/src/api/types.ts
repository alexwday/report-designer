// ============================================================
// Literal Types
// ============================================================

export type OutputFormat = 'pdf' | 'ppt';
export type Orientation = 'landscape' | 'portrait';
export type TemplateStatus = 'draft' | 'active' | 'archived';
export type WidgetType = 'summary' | 'key_points' | 'table' | 'chart' | 'comparison' | 'custom';
export type ContentType = 'text' | 'markdown' | 'html' | 'json';
export type GeneratedBy = 'agent' | 'user_edit' | 'import';
export type ChartType = 'bar' | 'line';

// ============================================================
// Template Models
// ============================================================

export interface Template {
  id: string;
  name: string;
  description: string | null;
  created_by: string;
  output_format: OutputFormat;
  orientation: Orientation | null;
  status: TemplateStatus;
  formatting_profile?: FormattingProfile | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface TemplateSummary {
  id: string;
  name: string;
  description: string | null;
  created_by: string;
  output_format: OutputFormat;
  status: TemplateStatus;
  formatting_profile?: FormattingProfile | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface CreateTemplateRequest {
  name: string;
  description?: string;
  output_format?: OutputFormat;
  orientation?: Orientation;
  formatting_profile?: FormattingProfile;
}

export interface UpdateTemplateRequest {
  name?: string;
  description?: string;
  output_format?: OutputFormat;
  orientation?: Orientation;
  status?: TemplateStatus;
  formatting_profile?: FormattingProfile;
}

// ============================================================
// Section Models
// ============================================================

export interface SubsectionBasic {
  id: string;
  title: string | null;
  position: number;
  widget_type: string | null;
  data_source_config: DataSourceConfig | null;
  has_notes: boolean;
  has_instructions: boolean;
  content_type: string | null;
  version_number: number;
}

export interface Section {
  id: string;
  position: number;
  title: string | null;
  created_at: string | null;
  updated_at: string | null;
  subsections: SubsectionBasic[];
}

export interface CreateSectionRequest {
  title?: string;
  position?: number;
}

export interface UpdateSectionRequest {
  title?: string;
  position?: number;
}

export interface SectionDeleteResponse {
  deleted: boolean;
  section_id: string;
}

// ============================================================
// Subsection Models
// ============================================================

export interface VersionSummary {
  id: string;
  version_number: number;
  instructions: string | null;
  notes: string | null;
  content_preview: string | null;
  content_type: string | null;
  generated_by: string | null;
  is_final: boolean;
  created_at: string | null;
}

export interface Version {
  id: string;
  subsection_id: string;
  version_number: number;
  instructions: string | null;
  notes: string | null;
  content: string | null;
  content_type: string | null;
  generated_by: string | null;
  is_final: boolean;
  generation_context: Record<string, unknown> | null;
  created_at: string | null;
}

export interface Subsection {
  id: string;
  section_id: string;
  title: string | null;
  position: number;
  widget_type: string | null;
  data_source_config: DataSourceConfig | null;
  notes: string | null;
  instructions: string | null;
  content: string | null;
  content_type: string | null;
  version_number: number;
  created_at: string | null;
  updated_at: string | null;
  template_id: string;
  section_title: string | null;
  versions?: VersionSummary[];
}

export interface CreateSubsectionRequest {
  title?: string;
  position?: number;
}

export interface CreateSubsectionResponse {
  id: string;
  section_id: string;
  title: string | null;
  position: number;
  widget_type: string | null;
  created_at: string | null;
}

export interface UpdateTitleRequest {
  title: string;
}

export interface UpdateTitleResponse {
  id: string;
  title: string | null;
  updated: boolean;
}

export interface ReorderSubsectionRequest {
  new_position: number;
}

export interface SubsectionDeleteResponse {
  deleted: boolean;
  subsection_id: string;
}

export interface UpdateNotesRequest {
  notes: string;
  append?: boolean;
}

export interface UpdateNotesResponse {
  id: string;
  notes: string | null;
  updated: boolean;
}

export interface UpdateInstructionsRequest {
  instructions: string;
}

export interface UpdateInstructionsResponse {
  id: string;
  instructions: string | null;
  updated: boolean;
}

export interface SaveVersionRequest {
  content: string;
  content_type?: ContentType;
  generated_by?: GeneratedBy;
  is_final?: boolean;
  generation_context?: Record<string, unknown>;
  title?: string;
}

export interface SaveVersionResponse {
  version_id: string;
  version_number: number;
  subsection_id: string;
  content_type: string;
  generated_by: string;
  is_final: boolean;
  title?: string | null;
  created_at: string | null;
}

// ============================================================
// Data Source Models
// ============================================================

export interface DataInputConfig {
  source_id: string;
  method_id: string;
  parameters?: Record<string, unknown>;
}

export interface ContextDependencies {
  section_ids?: string[];
  subsection_ids?: string[];
}

export interface VisualizationConfig {
  chart_type?: ChartType;
  title?: string;
  x_key?: string;
  y_key?: string;
  series_key?: string;
  metric_id?: string;
}

export interface DataSourceConfig {
  inputs: DataInputConfig[];
  dependencies?: ContextDependencies;
  visualization?: VisualizationConfig;
}

export interface FormattingProfile {
  theme_id: string;
  theme_name?: string;
  font_family?: string;
  title_font_size_pt?: number;
  subsection_title_font_size_pt?: number;
  body_font_size_pt?: number;
  line_height?: number;
  accent_color?: string;
  heading_color?: string;
  body_color?: string;
  section_title_case?: 'title' | 'sentence' | 'upper';
  subsection_title_case?: 'title' | 'sentence' | 'upper';
}

export interface DataSourceRegistry {
  id: string;
  name: string;
  description: string;
  category: string;
  retrieval_methods: RetrievalMethod[];
  suggested_widgets: string[] | null;
  is_active: boolean;
  created_at: string | null;
}

export interface RetrievalMethod {
  method_id: string;
  id?: string; // backward compatibility for any older payloads
  name: string;
  description: string;
  parameters: ParameterDefinition[];
}

export interface ParameterDefinition {
  key?: string;
  name?: string; // legacy alias
  type: string;
  required?: boolean;
  prompt?: string;
  description?: string;
  options?: string[];
  enum?: string[];
  default?: unknown;
  items?: {
    type?: string;
    options?: string[];
    enum?: string[];
    properties?: Record<string, unknown>;
  };
}

export interface ConfigureSubsectionRequest {
  widget_type?: WidgetType;
  data_source_config?: DataSourceConfig | null;
}

export interface ConfigureSubsectionResponse {
  id: string;
  widget_type: string | null;
  data_source_config: DataSourceConfig | null;
  updated: boolean;
}

// ============================================================
// Chat Models
// ============================================================

export interface ChatRequest {
  message: string;
  focus_section_id?: string;
  focus_subsection_id?: string;
}

export interface ToolCallLog {
  tool: string;
  args: Record<string, unknown>;
  result?: unknown;
  error?: string;
}

export interface ChatResponse {
  response: string;
  tool_calls: ToolCallLog[];
  conversation_id: string;
}

export interface ConversationMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
}

export interface ConversationHistoryResponse {
  conversation_id: string;
  messages: ConversationMessage[];
}

// ============================================================
// Preview/Export Models
// ============================================================

export interface PreviewSubsection {
  id: string;
  title: string | null;
  position: number;
  widget_type: string | null;
  data_source_config: DataSourceConfig | null;
  has_notes: boolean;
  has_instructions: boolean;
  content_type: string | null;
  version_number: number;
  content: string | null;
  notes: string | null;
  instructions: string | null;
}

export interface PreviewSection {
  id: string;
  position: number;
  title: string | null;
  created_at: string | null;
  updated_at: string | null;
  subsections: PreviewSubsection[];
}

export interface PreviewData {
  template: Template;
  sections: PreviewSection[];
}

// ============================================================
// Generation Models
// ============================================================

export type GenerationStatusType = 'pending' | 'in_progress' | 'completed' | 'failed';

export interface SubsectionGenerationProgress {
  subsection_id: string;
  title: string | null;
  position: number;
  section_title: string;
  widget_type?: string | null;
  status: GenerationStatusType;
  error: string | null;
}

export interface GenerationJobStatus {
  job_id: string;
  template_id: string;
  status: GenerationStatusType;
  current_index: number;
  total_subsections: number;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  subsections: SubsectionGenerationProgress[];
}

export interface StartGenerationResponse {
  job_id: string;
  total_subsections: number;
}

export interface StartGenerationRequest {
  run_inputs?: Record<string, unknown>;
}

export interface GenerationBlockingError {
  subsection_id: string;
  subsection_title: string | null;
  subsection_position: number;
  section_title: string;
  reason: string;
}

export interface GenerationRequiredInput {
  key: string;
  label: string;
  type: string;
  options?: unknown[] | null;
  used_by: Array<{
    subsection_id: string;
    section_title: string;
    subsection_title: string | null;
    parameter_key: string;
  }>;
}

export interface GenerationRequirementsResponse {
  ready: boolean;
  required_inputs: GenerationRequiredInput[];
  blocking_errors: GenerationBlockingError[];
  subsections_considered: number;
  saved_run_inputs: Record<string, unknown>;
}

export interface GenerateSubsectionResponse {
  generated: boolean;
  subsection_id: string;
  version_id: string;
  version_number: number;
}

export interface GeneratedSectionSubsection {
  subsection_id: string;
  version_id: string;
  version_number: number;
}

export interface GenerateSectionResponse {
  generated: boolean;
  section_id: string;
  generated_count: number;
  generated_subsections: GeneratedSectionSubsection[];
}

// ============================================================
// Upload Models
// ============================================================

export interface Upload {
  id: string;
  template_id?: string;
  filename: string;
  original_filename: string;
  content_type: string | null;
  size_bytes: number;
  extraction_status: 'pending' | 'completed' | 'failed';
  extraction_error?: string | null;
  has_extracted_text?: boolean;
  created_at: string | null;
}

// ============================================================
// Template Version Models
// ============================================================

export interface TemplateVersionSummary {
  id: string;
  template_id: string;
  version_number: number;
  name: string;
  created_by: string | null;
  created_at: string | null;
}

export interface TemplateVersionFull {
  id: string;
  template_id: string;
  version_number: number;
  name: string;
  snapshot: TemplateSnapshot;
  created_by: string | null;
  created_at: string | null;
}

export interface TemplateSnapshot {
  template: {
    name: string;
    description: string | null;
    output_format: OutputFormat;
    orientation: Orientation | null;
    status: TemplateStatus;
    formatting_profile?: FormattingProfile | null;
  };
  sections: SnapshotSection[];
}

export interface SnapshotSection {
  id: string;
  position: number;
  title: string | null;
  subsections: SnapshotSubsection[];
}

export interface SnapshotSubsection {
  id: string;
  title: string | null;
  position: number;
  widget_type: string | null;
  data_source_config: DataSourceConfig | null;
  notes: string | null;
  instructions: string | null;
  content: string | null;
  content_type: string | null;
  version_number: number;
}

export interface CreateTemplateVersionRequest {
  name?: string;
}

export interface RestoreVersionResponse {
  success: boolean;
  template_id: string;
  restored_from: string;
  sections_restored: number;
}

export interface ForkTemplateRequest {
  new_name: string;
}

export interface ForkTemplateResponse {
  id: string;
  name: string;
  description: string | null;
  created_by: string;
  output_format: OutputFormat;
  orientation: Orientation | null;
  status: TemplateStatus;
  created_at: string | null;
  formatting_profile?: FormattingProfile | null;
  forked_from: string;
}

export interface SetSharedRequest {
  is_shared: boolean;
}

export interface SetSharedResponse {
  id: string;
  name: string;
  is_shared: boolean;
}

// ============================================================
// Helper function
// ============================================================

/**
 * Convert subsection position (1, 2, 3) to letter label (A, B, C)
 */
export function positionToLabel(position: number): string {
  return String.fromCharCode(64 + position); // 1 -> A, 2 -> B, etc.
}
