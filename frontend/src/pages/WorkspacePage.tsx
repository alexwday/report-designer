import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { toast } from 'sonner';
import {
  useTemplate,
  useUpdateTemplate,
  useExportPdf,
  useStartGeneration,
  useGenerationRequirements,
} from '../api/queries';
import { useWorkspaceStore } from '../store/workspace';
import { SectionNav } from '../components/SectionNav';
import { SectionEditor } from '../components/SectionEditor';
import { ChatPanel } from '../components/ChatPanel';
import { ReportPreview } from '../components/ReportPreview';
import { GenerationProgress } from '../components/GenerationProgress';
import { FileUpload } from '../components/FileUpload';
import { TemplateVersions } from '../components/TemplateVersions';
import type {
  FormattingProfile,
  OutputFormat,
  Orientation,
  GenerationRequiredInput,
  GenerationBlockingError,
} from '../api/types';

function isMissingValue(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === 'string' && value.trim() === '') return true;
  if (Array.isArray(value) && value.length === 0) return true;
  if (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0) return true;
  return false;
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (
    typeof error === 'object'
    && error !== null
    && 'response' in error
  ) {
    const response = (error as { response?: unknown }).response;
    if (
      typeof response === 'object'
      && response !== null
      && 'data' in response
    ) {
      const data = (response as { data?: unknown }).data;
      if (
        typeof data === 'object'
        && data !== null
        && 'detail' in data
      ) {
        const detail = (data as { detail: unknown }).detail;
        if (typeof detail === 'string') return detail;
        if (
          typeof detail === 'object'
          && detail !== null
          && 'validation_errors' in detail
          && Array.isArray((detail as { validation_errors?: unknown[] }).validation_errors)
          && (detail as { validation_errors: unknown[] }).validation_errors.length > 0
        ) {
          const first = (detail as { validation_errors: unknown[] }).validation_errors[0];
          if (typeof first === 'string') return first;
          if (typeof first === 'object' && first !== null && 'reason' in first && typeof first.reason === 'string') {
            return first.reason;
          }
        }
      }
    }
  }
  return fallback;
}

const THEME_PRESETS: Array<{
  id: string;
  name: string;
  description: string;
  profile: FormattingProfile;
}> = [
  {
    id: 'executive_blue',
    name: 'Executive Blue',
    description: 'Balanced corporate style with blue accents.',
    profile: {
      theme_id: 'executive_blue',
      theme_name: 'Executive Blue',
      font_family: "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
      title_font_size_pt: 20,
      subsection_title_font_size_pt: 13,
      body_font_size_pt: 11,
      line_height: 1.6,
      accent_color: '#1D4ED8',
      heading_color: '#111827',
      body_color: '#1F2937',
      section_title_case: 'title',
      subsection_title_case: 'title',
    },
  },
  {
    id: 'modern_slate',
    name: 'Modern Slate',
    description: 'Clean sans-serif with teal accents.',
    profile: {
      theme_id: 'modern_slate',
      theme_name: 'Modern Slate',
      font_family: "'Avenir Next', 'Segoe UI', Arial, sans-serif",
      title_font_size_pt: 21,
      subsection_title_font_size_pt: 13,
      body_font_size_pt: 11,
      line_height: 1.55,
      accent_color: '#0F766E',
      heading_color: '#0F172A',
      body_color: '#334155',
      section_title_case: 'sentence',
      subsection_title_case: 'sentence',
    },
  },
  {
    id: 'print_serif',
    name: 'Print Serif',
    description: 'Traditional print-oriented serif look.',
    profile: {
      theme_id: 'print_serif',
      theme_name: 'Print Serif',
      font_family: "'Georgia', 'Times New Roman', serif",
      title_font_size_pt: 22,
      subsection_title_font_size_pt: 14,
      body_font_size_pt: 11,
      line_height: 1.65,
      accent_color: '#9A3412',
      heading_color: '#1C1917',
      body_color: '#292524',
      section_title_case: 'title',
      subsection_title_case: 'title',
    },
  },
];

const DEFAULT_THEME_ID = 'executive_blue';

function getThemePreset(themeId: string | undefined): FormattingProfile {
  const match = THEME_PRESETS.find((preset) => preset.id === themeId);
  if (match) return { ...match.profile };
  return { ...THEME_PRESETS[0].profile };
}

function normalizeFormattingProfile(profile: FormattingProfile | null | undefined): FormattingProfile {
  const themeId = profile?.theme_id || DEFAULT_THEME_ID;
  const base = getThemePreset(themeId);
  return { ...base, ...(profile || {}), theme_id: themeId };
}

export function WorkspacePage() {
  const { templateId } = useParams<{ templateId: string }>();
  const navigate = useNavigate();
  const { reset } = useWorkspaceStore();

  // View mode: 'edit' or 'preview'
  const [viewMode, setViewMode] = useState<'edit' | 'preview'>('edit');

  // Generation state
  const [generationJobId, setGenerationJobId] = useState<string | null>(null);
  const [isRunInputsModalOpen, setIsRunInputsModalOpen] = useState(false);
  const [requiredInputs, setRequiredInputs] = useState<GenerationRequiredInput[]>([]);
  const [runInputValues, setRunInputValues] = useState<Record<string, unknown>>({});
  const [runInputErrors, setRunInputErrors] = useState<Record<string, string>>({});
  const [isBlockingErrorsModalOpen, setIsBlockingErrorsModalOpen] = useState(false);
  const [blockingErrors, setBlockingErrors] = useState<GenerationBlockingError[]>([]);

  // Modal states
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isVersionModalOpen, setIsVersionModalOpen] = useState(false);
  const [isFormattingModalOpen, setIsFormattingModalOpen] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editFormat, setEditFormat] = useState<OutputFormat>('pdf');
  const [editOrientation, setEditOrientation] = useState<Orientation>('portrait');
  const [formattingProfileDraft, setFormattingProfileDraft] = useState<FormattingProfile>(
    getThemePreset(DEFAULT_THEME_ID)
  );

  const { data: template, isLoading, error } = useTemplate(templateId || '');
  const updateTemplate = useUpdateTemplate();
  const exportPdf = useExportPdf(templateId || '');
  const startGeneration = useStartGeneration(templateId || '');
  const generationRequirements = useGenerationRequirements(templateId || '');

  const coerceRunInput = (
    input: GenerationRequiredInput,
    rawValue: unknown,
  ): { value?: unknown; error?: string } => {
    const inputType = input.type.toLowerCase();
    const options = Array.isArray(input.options) ? input.options : [];

    if (inputType === 'integer') {
      const parsed = typeof rawValue === 'number' ? rawValue : Number.parseInt(String(rawValue), 10);
      if (!Number.isInteger(parsed)) return { error: 'Must be an integer' };
      return { value: parsed };
    }

    if (inputType === 'number') {
      const parsed = typeof rawValue === 'number' ? rawValue : Number.parseFloat(String(rawValue));
      if (Number.isNaN(parsed)) return { error: 'Must be a number' };
      return { value: parsed };
    }

    if (inputType === 'boolean') {
      if (typeof rawValue === 'boolean') return { value: rawValue };
      const normalized = String(rawValue).trim().toLowerCase();
      if (normalized === 'true' || normalized === '1' || normalized === 'yes') return { value: true };
      if (normalized === 'false' || normalized === '0' || normalized === 'no') return { value: false };
      return { error: 'Must be true or false' };
    }

    if (inputType === 'array') {
      if (Array.isArray(rawValue)) return { value: rawValue };
      const parsed = String(rawValue)
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean);
      return { value: parsed };
    }

    if (inputType === 'object') {
      if (typeof rawValue === 'object' && rawValue !== null && !Array.isArray(rawValue)) {
        return { value: rawValue };
      }
      try {
        const parsed = JSON.parse(String(rawValue));
        if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
          return { error: 'Must be a JSON object' };
        }
        return { value: parsed };
      } catch {
        return { error: 'Must be valid JSON' };
      }
    }

    const normalized = String(rawValue).trim();
    if (options.length > 0 && !options.includes(normalized)) {
      return { error: `Must be one of: ${options.join(', ')}` };
    }
    return { value: normalized };
  };

  const buildRunInputsForSubmit = (): Record<string, unknown> | null => {
    const nextErrors: Record<string, string> = {};
    const nextInputs: Record<string, unknown> = {};

    for (const requiredInput of requiredInputs) {
      const rawValue = runInputValues[requiredInput.key];
      if (isMissingValue(rawValue)) {
        nextErrors[requiredInput.key] = 'Required input';
        continue;
      }
      const coerced = coerceRunInput(requiredInput, rawValue);
      if (coerced.error) {
        nextErrors[requiredInput.key] = coerced.error;
        continue;
      }
      nextInputs[requiredInput.key] = coerced.value;
    }

    setRunInputErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return null;
    return nextInputs;
  };

  const launchGeneration = async (runInputs?: Record<string, unknown>) => {
    try {
      const request = runInputs ? { run_inputs: runInputs } : undefined;
      const result = await startGeneration.mutateAsync(request);
      setGenerationJobId(result.job_id);
      toast.info('Generation started');
      return true;
    } catch (err) {
      console.error('Failed to start generation:', err);
      toast.error(getErrorMessage(err, 'Failed to start generation. Check subsection data source configuration.'));
      return false;
    }
  };

  const handleGenerateAll = async () => {
    try {
      const requirements = await generationRequirements.mutateAsync();

      if (requirements.blocking_errors.length > 0) {
        setBlockingErrors(requirements.blocking_errors);
        setIsBlockingErrorsModalOpen(true);
        toast.error('Generation is blocked. Fix subsection configuration first.');
        return;
      }

      if (requirements.required_inputs.length > 0) {
        const savedRunInputs = requirements.saved_run_inputs || {};
        setRequiredInputs(requirements.required_inputs);
        setRunInputValues((previous) => {
          const next: Record<string, unknown> = {};
          for (const requiredInput of requirements.required_inputs) {
            const existing = previous[requiredInput.key];
            if (existing !== undefined) {
              next[requiredInput.key] = existing;
              continue;
            }
            const savedValue = savedRunInputs[requiredInput.key];
            if (savedValue !== undefined) {
              next[requiredInput.key] = savedValue;
              continue;
            }
            if (
              requiredInput.key.endsWith('_period_fiscal_year')
              && savedRunInputs.period_fiscal_year !== undefined
            ) {
              next[requiredInput.key] = savedRunInputs.period_fiscal_year;
              continue;
            }
            if (
              requiredInput.key.endsWith('_period_fiscal_quarter')
              && savedRunInputs.period_fiscal_quarter !== undefined
            ) {
              next[requiredInput.key] = savedRunInputs.period_fiscal_quarter;
              continue;
            }
            if (requiredInput.type.toLowerCase() === 'boolean') {
              next[requiredInput.key] = '';
              continue;
            }
            if (Array.isArray(requiredInput.options) && requiredInput.options.length > 0) {
              next[requiredInput.key] = String(requiredInput.options[0]);
              continue;
            }
            next[requiredInput.key] = '';
          }
          return next;
        });
        setRunInputErrors({});
        setIsRunInputsModalOpen(true);
        return;
      }

      await launchGeneration();
    } catch (err) {
      console.error('Failed to check generation requirements:', err);
      toast.error(getErrorMessage(err, 'Failed to check generation requirements.'));
    }
  };

  const handleRunInputChange = (inputKey: string, value: unknown) => {
    setRunInputValues((previous) => ({ ...previous, [inputKey]: value }));
    setRunInputErrors((previous) => {
      const next = { ...previous };
      delete next[inputKey];
      return next;
    });
  };

  const handleRunInputsSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const runInputs = buildRunInputsForSubmit();
    if (!runInputs) {
      toast.error('Please fix run input errors before starting generation.');
      return;
    }
    const started = await launchGeneration(runInputs);
    if (started) {
      setIsRunInputsModalOpen(false);
    }
  };

  const handleGenerationClose = () => {
    setGenerationJobId(null);
  };

  const handleGenerationComplete = () => {
    setGenerationJobId(null);
    toast.success('Generation complete!');
  };

  const handleExport = async () => {
    try {
      const blob = await exportPdf.mutateAsync();
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${template?.name || 'report'}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success('PDF exported successfully');
    } catch (err) {
      console.error('Failed to export PDF:', err);
      toast.error('Failed to export PDF. Please try again.');
    }
  };

  // Sync edit form with template data when modal opens
  const openEditModal = () => {
    if (template) {
      setEditName(template.name);
      setEditDescription(template.description || '');
      setEditFormat(template.output_format);
      setEditOrientation(template.orientation || 'portrait');
      setIsEditModalOpen(true);
    }
  };

  const openFormattingModal = () => {
    const normalized = normalizeFormattingProfile(template?.formatting_profile || null);
    setFormattingProfileDraft(normalized);
    setIsFormattingModalOpen(true);
  };

  const handleSelectFormattingTheme = (themeId: string) => {
    setFormattingProfileDraft(getThemePreset(themeId));
  };

  const handleFormattingFieldChange = <K extends keyof FormattingProfile>(
    key: K,
    value: FormattingProfile[K]
  ) => {
    setFormattingProfileDraft((previous) => ({ ...previous, [key]: value }));
  };

  const handleSaveTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!templateId) return;

    try {
      await updateTemplate.mutateAsync({
        id: templateId,
        name: editName,
        description: editDescription || undefined,
        output_format: editFormat,
        orientation: editOrientation,
      });
      setIsEditModalOpen(false);
      toast.success('Template updated');
    } catch (err) {
      console.error('Failed to update template:', err);
      toast.error('Failed to update template');
    }
  };

  const handleSaveFormatting = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!templateId) return;

    try {
      await updateTemplate.mutateAsync({
        id: templateId,
        formatting_profile: normalizeFormattingProfile(formattingProfileDraft),
      });
      setIsFormattingModalOpen(false);
      toast.success('Formatting profile updated');
    } catch (err) {
      console.error('Failed to update formatting profile:', err);
      toast.error('Failed to update formatting profile');
    }
  };

  // Reset workspace state when entering a new template
  useEffect(() => {
    reset();
  }, [templateId, reset]);

  if (!templateId) {
    navigate('/');
    return null;
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
        <div className="text-zinc-500">Loading template...</div>
      </div>
    );
  }

  if (error || !template) {
    return (
      <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 mb-4">Template not found</p>
          <Link to="/" className="text-sky-600 hover:underline">
            Back to templates
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-zinc-50 flex flex-col overflow-hidden">
      {/* Header */}
      <header className="bg-gradient-to-b from-zinc-100 to-zinc-200/70 border-b border-zinc-300/80 shadow-[0_1px_0_rgba(15,23,42,0.06)] px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="p-2 text-zinc-400 hover:text-zinc-600"
            title="Back to templates"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div className="flex flex-col gap-1">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 px-1">Title</p>
            <div className="flex items-center gap-2">
              <button
                onClick={openEditModal}
                className="text-lg font-semibold text-zinc-900 hover:text-sky-600 transition-colors flex items-center gap-1"
                title="Click to edit template details"
              >
                {template.name}
                <svg className="w-4 h-4 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
              </button>
              <span className="px-2 py-0.5 text-xs bg-zinc-100 text-zinc-600 rounded">
                {template.output_format}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-start gap-5 flex-wrap justify-end">
          <div className="flex flex-col gap-1">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 px-1">Editor</p>
            <div className="inline-flex rounded-xl border border-zinc-300/90 overflow-hidden bg-gradient-to-b from-white to-zinc-50 shadow-[0_4px_14px_rgba(15,23,42,0.10)] ring-1 ring-white/80">
              <button
                onClick={() => setViewMode('edit')}
                className={`px-4 py-2.5 text-sm font-medium transition-colors ${
                  viewMode === 'edit'
                    ? 'bg-zinc-900 text-white shadow-inner'
                    : 'text-zinc-700 hover:bg-white'
                }`}
              >
                Edit
              </button>
              <button
                onClick={openFormattingModal}
                className="px-4 py-2.5 text-sm font-medium text-zinc-700 border-l border-zinc-300/90 hover:bg-white transition-colors"
                title="Choose and tweak document formatting theme"
              >
                Format
              </button>
              <button
                onClick={() => setViewMode('preview')}
                className={`px-4 py-2.5 text-sm font-medium border-l border-zinc-300/90 transition-colors ${
                  viewMode === 'preview'
                    ? 'bg-zinc-900 text-white shadow-inner'
                    : 'text-zinc-700 hover:bg-white'
                }`}
              >
                Preview
              </button>
            </div>
          </div>

          <div className="hidden lg:block w-px h-14 bg-zinc-300/80 self-end mb-1" aria-hidden="true"></div>

          <div className="flex flex-col gap-1">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 px-1">Output</p>
            <div className="inline-flex rounded-xl border border-zinc-300/90 overflow-hidden bg-gradient-to-b from-white to-zinc-50 shadow-[0_4px_14px_rgba(15,23,42,0.10)] ring-1 ring-white/80">
              <button
                onClick={handleGenerateAll}
                disabled={startGeneration.isPending || generationRequirements.isPending}
                className="px-4 py-2.5 text-sm font-medium bg-green-600 text-white hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 border-r border-zinc-300/90"
              >
                {startGeneration.isPending ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Starting...
                  </>
                ) : generationRequirements.isPending ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Checking...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    Generate
                  </>
                )}
              </button>
              <button
                onClick={handleExport}
                disabled={exportPdf.isPending}
                className="px-4 py-2.5 text-sm font-medium bg-zinc-900 text-white hover:bg-zinc-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 border-r border-zinc-300/90"
              >
                {exportPdf.isPending ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Exporting...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Export
                  </>
                )}
              </button>
              <button
                onClick={() => setIsVersionModalOpen(true)}
                className="px-4 py-2.5 text-sm font-medium text-zinc-700 hover:bg-white transition-colors flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                History
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      {viewMode === 'preview' ? (
        <ReportPreview templateId={templateId} />
      ) : (
        <>
          <div className="flex-1 overflow-hidden bg-gradient-to-br from-zinc-100 to-zinc-200/50 p-3">
            <div className="h-full flex gap-3 overflow-hidden">
              <SectionNav
                templateId={templateId}
                onOpenDocuments={() => setIsUploadModalOpen(true)}
              />
              <SectionEditor templateId={templateId} />
              <ChatPanel templateId={templateId} />
            </div>
          </div>
        </>
      )}

      {/* Edit Template Modal */}
      {isEditModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="px-6 py-4 border-b border-zinc-200">
              <h2 className="text-lg font-semibold text-zinc-900">Edit Template</h2>
            </div>
            <form onSubmit={handleSaveTemplate}>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-zinc-700 mb-1">
                    Name
                  </label>
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-700 mb-1">
                    Description
                  </label>
                  <textarea
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 resize-none"
                    rows={3}
                    placeholder="Optional description..."
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-zinc-700 mb-1">
                      Format
                    </label>
                    <select
                      value={editFormat}
                      onChange={(e) => setEditFormat(e.target.value as OutputFormat)}
                      className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    >
                      <option value="pdf">PDF</option>
                      <option value="ppt">PowerPoint</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-zinc-700 mb-1">
                      Orientation
                    </label>
                    <select
                      value={editOrientation}
                      onChange={(e) => setEditOrientation(e.target.value as Orientation)}
                      className="w-full px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    >
                      <option value="portrait">Portrait</option>
                      <option value="landscape">Landscape</option>
                    </select>
                  </div>
                </div>
              </div>
              <div className="px-6 py-4 border-t border-zinc-200 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsEditModalOpen(false)}
                  className="px-4 py-2 text-sm text-zinc-700 hover:text-zinc-900"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateTemplate.isPending}
                  className="px-4 py-2 text-sm bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 disabled:opacity-50"
                >
                  {updateTemplate.isPending ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Formatting Theme Modal */}
      {isFormattingModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl mx-4 max-h-[85vh] overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-zinc-200">
              <h2 className="text-lg font-semibold text-zinc-900">Formatting Theme</h2>
              <p className="text-sm text-zinc-500 mt-1">
                Pick a base theme, then tweak typography and color tokens.
              </p>
            </div>
            <form onSubmit={handleSaveFormatting} className="flex-1 overflow-y-auto">
              <div className="p-6 space-y-6">
                <div>
                  <h3 className="text-sm font-semibold text-zinc-900 mb-3">Theme presets</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {THEME_PRESETS.map((theme) => {
                      const isSelected = formattingProfileDraft.theme_id === theme.id;
                      return (
                        <button
                          key={theme.id}
                          type="button"
                          onClick={() => handleSelectFormattingTheme(theme.id)}
                          className={`text-left border rounded-lg p-3 transition-colors ${
                            isSelected
                              ? 'border-sky-400 bg-sky-50'
                              : 'border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50'
                          }`}
                        >
                          <p className="text-sm font-medium text-zinc-900">{theme.name}</p>
                          <p className="text-xs text-zinc-500 mt-1">{theme.description}</p>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wide text-zinc-500 mb-1">
                      Font family
                    </label>
                    <input
                      type="text"
                      value={formattingProfileDraft.font_family || ''}
                      onChange={(e) => handleFormattingFieldChange('font_family', e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wide text-zinc-500 mb-1">
                      Line height
                    </label>
                    <input
                      type="number"
                      step="0.05"
                      min="1.2"
                      max="2.2"
                      value={formattingProfileDraft.line_height || 1.6}
                      onChange={(e) => {
                        const parsed = Number.parseFloat(e.target.value);
                        handleFormattingFieldChange('line_height', Number.isFinite(parsed) ? parsed : 1.6);
                      }}
                      className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wide text-zinc-500 mb-1">
                      Section title size (pt)
                    </label>
                    <input
                      type="number"
                      min="14"
                      max="36"
                      value={formattingProfileDraft.title_font_size_pt || 20}
                      onChange={(e) => {
                        const parsed = Number.parseInt(e.target.value, 10);
                        handleFormattingFieldChange('title_font_size_pt', Number.isFinite(parsed) ? parsed : 20);
                      }}
                      className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wide text-zinc-500 mb-1">
                      Subsection title size (pt)
                    </label>
                    <input
                      type="number"
                      min="10"
                      max="28"
                      value={formattingProfileDraft.subsection_title_font_size_pt || 13}
                      onChange={(e) => {
                        const parsed = Number.parseInt(e.target.value, 10);
                        handleFormattingFieldChange('subsection_title_font_size_pt', Number.isFinite(parsed) ? parsed : 13);
                      }}
                      className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wide text-zinc-500 mb-1">
                      Body size (pt)
                    </label>
                    <input
                      type="number"
                      min="9"
                      max="18"
                      value={formattingProfileDraft.body_font_size_pt || 11}
                      onChange={(e) => {
                        const parsed = Number.parseInt(e.target.value, 10);
                        handleFormattingFieldChange('body_font_size_pt', Number.isFinite(parsed) ? parsed : 11);
                      }}
                      className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wide text-zinc-500 mb-1">
                      Section title case
                    </label>
                    <select
                      value={formattingProfileDraft.section_title_case || 'title'}
                      onChange={(e) => handleFormattingFieldChange('section_title_case', e.target.value as FormattingProfile['section_title_case'])}
                      className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    >
                      <option value="title">Title Case</option>
                      <option value="sentence">Sentence case</option>
                      <option value="upper">UPPERCASE</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wide text-zinc-500 mb-1">
                      Subsection title case
                    </label>
                    <select
                      value={formattingProfileDraft.subsection_title_case || 'title'}
                      onChange={(e) => handleFormattingFieldChange('subsection_title_case', e.target.value as FormattingProfile['subsection_title_case'])}
                      className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    >
                      <option value="title">Title Case</option>
                      <option value="sentence">Sentence case</option>
                      <option value="upper">UPPERCASE</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wide text-zinc-500 mb-1">
                      Accent color
                    </label>
                    <input
                      type="color"
                      value={formattingProfileDraft.accent_color || '#1D4ED8'}
                      onChange={(e) => handleFormattingFieldChange('accent_color', e.target.value)}
                      className="w-full h-10 border border-zinc-300 rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wide text-zinc-500 mb-1">
                      Heading color
                    </label>
                    <input
                      type="color"
                      value={formattingProfileDraft.heading_color || '#111827'}
                      onChange={(e) => handleFormattingFieldChange('heading_color', e.target.value)}
                      className="w-full h-10 border border-zinc-300 rounded-lg"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wide text-zinc-500 mb-1">
                      Body color
                    </label>
                    <input
                      type="color"
                      value={formattingProfileDraft.body_color || '#1F2937'}
                      onChange={(e) => handleFormattingFieldChange('body_color', e.target.value)}
                      className="w-full h-10 border border-zinc-300 rounded-lg"
                    />
                  </div>
                </div>
              </div>
              <div className="px-6 py-4 border-t border-zinc-200 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsFormattingModalOpen(false)}
                  className="px-4 py-2 text-sm text-zinc-700 hover:text-zinc-900"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateTemplate.isPending}
                  className="px-4 py-2 text-sm bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 disabled:opacity-50"
                >
                  {updateTemplate.isPending ? 'Saving...' : 'Save formatting'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Generation Progress Modal */}
      {generationJobId && templateId && (
        <GenerationProgress
          templateId={templateId}
          jobId={generationJobId}
          onClose={handleGenerationClose}
          onComplete={handleGenerationComplete}
        />
      )}

      {/* Generation run inputs modal */}
      {isRunInputsModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[85vh] overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-zinc-200">
              <h2 className="text-lg font-semibold text-zinc-900">Initialize Generation Inputs</h2>
              <p className="text-sm text-zinc-500 mt-1">
                Set variable values for this run before generating content.
              </p>
            </div>
            <form onSubmit={handleRunInputsSubmit} className="flex-1 overflow-y-auto">
              <div className="p-6 space-y-4">
                {requiredInputs.map((requiredInput) => {
                  const inputType = requiredInput.type.toLowerCase();
                  const options = Array.isArray(requiredInput.options) ? requiredInput.options : [];
                  const value = runInputValues[requiredInput.key];
                  const useCount = requiredInput.used_by.length;

                  return (
                    <div key={requiredInput.key}>
                      <label className="block text-sm font-medium text-zinc-700 mb-1">
                        {requiredInput.label}
                      </label>
                      <p className="text-xs text-zinc-500 mb-2">
                        Variable: <span className="font-mono">{requiredInput.key}</span>
                        {' • '}
                        Used by {useCount} subsection{useCount === 1 ? '' : 's'}
                      </p>

                      {options.length > 0 && (
                        <select
                          value={typeof value === 'string' ? value : ''}
                          onChange={(e) => handleRunInputChange(requiredInput.key, e.target.value)}
                          className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                        >
                          <option value="">Select...</option>
                          {options.map((option) => (
                            <option key={String(option)} value={String(option)}>
                              {String(option)}
                            </option>
                          ))}
                        </select>
                      )}

                      {options.length === 0 && inputType === 'boolean' && (
                        <select
                          value={typeof value === 'string' ? value : ''}
                          onChange={(e) => handleRunInputChange(requiredInput.key, e.target.value)}
                          className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                        >
                          <option value="">Select...</option>
                          <option value="true">True</option>
                          <option value="false">False</option>
                        </select>
                      )}

                      {options.length === 0 && inputType === 'object' && (
                        <textarea
                          value={
                            typeof value === 'string'
                              ? value
                              : (value && typeof value === 'object' && !Array.isArray(value))
                                ? JSON.stringify(value, null, 2)
                                : ''
                          }
                          onChange={(e) => handleRunInputChange(requiredInput.key, e.target.value)}
                          rows={4}
                          placeholder='{"key":"value"}'
                          className="w-full px-3 py-2 text-sm font-mono border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                        />
                      )}

                      {options.length === 0 && inputType === 'array' && (
                        <textarea
                          value={
                            Array.isArray(value)
                              ? value.map((item) => String(item)).join(', ')
                              : typeof value === 'string'
                                ? value
                                : ''
                          }
                          onChange={(e) => handleRunInputChange(requiredInput.key, e.target.value)}
                          rows={2}
                          placeholder="Comma-separated values"
                          className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                        />
                      )}

                      {options.length === 0 && inputType !== 'boolean' && inputType !== 'object' && inputType !== 'array' && (
                        <input
                          type={inputType === 'integer' || inputType === 'number' ? 'number' : 'text'}
                          value={value === undefined || value === null ? '' : String(value)}
                          onChange={(e) => handleRunInputChange(requiredInput.key, e.target.value)}
                          className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                        />
                      )}

                      {runInputErrors[requiredInput.key] && (
                        <p className="text-xs text-red-600 mt-1">{runInputErrors[requiredInput.key]}</p>
                      )}
                    </div>
                  );
                })}
              </div>

              <div className="px-6 py-4 border-t border-zinc-200 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsRunInputsModalOpen(false)}
                  className="px-4 py-2 text-sm text-zinc-700 hover:text-zinc-900"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={startGeneration.isPending}
                  className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  {startGeneration.isPending ? 'Starting...' : 'Start Generation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Generation blocking errors modal */}
      {isBlockingErrorsModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[80vh] overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-zinc-200">
              <h2 className="text-lg font-semibold text-red-700">Generation Blocked</h2>
              <p className="text-sm text-zinc-600 mt-1">
                Fix the data source configuration issues below before generating.
              </p>
            </div>
            <div className="p-6 overflow-y-auto space-y-3">
              {blockingErrors.map((errorItem, index) => (
                <div key={`${errorItem.subsection_id}-${index}`} className="p-3 border border-red-200 bg-red-50 rounded-lg">
                  <p className="text-sm font-medium text-zinc-900">
                    {errorItem.section_title}
                    {' • '}
                    {errorItem.subsection_title || `Subsection ${errorItem.subsection_position}`}
                  </p>
                  <p className="text-sm text-red-700 mt-1">{errorItem.reason}</p>
                </div>
              ))}
            </div>
            <div className="px-6 py-4 border-t border-zinc-200 flex justify-end">
              <button
                type="button"
                onClick={() => setIsBlockingErrorsModalOpen(false)}
                className="px-4 py-2 text-sm bg-zinc-900 text-white rounded-lg hover:bg-zinc-800"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* File Upload Modal */}
      {isUploadModalOpen && templateId && (
        <FileUpload
          templateId={templateId}
          onClose={() => setIsUploadModalOpen(false)}
        />
      )}

      {/* Template Versions Modal */}
      {isVersionModalOpen && templateId && (
        <TemplateVersions
          templateId={templateId}
          onClose={() => setIsVersionModalOpen(false)}
        />
      )}
    </div>
  );
}
