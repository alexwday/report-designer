import { useEffect } from 'react';
import { toast } from 'sonner';
import { useSections, usePreview, useCreateSubsection, useDeleteSubsection, useGenerateSection, useDataSourceRegistry } from '../api/queries';
import { useWorkspaceStore } from '../store/workspace';
import { SubsectionWorkspace } from './SubsectionWorkspace';
import { positionToLabel } from '../api/types';
import type { PreviewSubsection } from '../api/types';

function getMethodId(method: { method_id?: string; id?: string }): string {
  return method.method_id || method.id || '';
}

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

interface SectionEditorProps {
  templateId: string;
}

export function SectionEditor({ templateId }: SectionEditorProps) {
  const {
    selectedSectionId,
    selectedSubsectionId,
    setSelectedSubsection,
    generatingSections,
    setSectionGenerating,
  } = useWorkspaceStore();

  const { data: sections } = useSections(templateId);
  const { data: preview } = usePreview(templateId);
  const { data: dataSources } = useDataSourceRegistry();
  const createSubsection = useCreateSubsection();
  const deleteSubsection = useDeleteSubsection();
  const generateSection = useGenerateSection(templateId);

  // Find current section
  const currentSection = sections?.find(s => s.id === selectedSectionId);
  const previewSection = preview?.sections.find(s => s.id === selectedSectionId);

  // Sort subsections by position
  const sortedSubsections = previewSection?.subsections
    .slice()
    .sort((a, b) => a.position - b.position);

  // Auto-select first subsection when section changes
  useEffect(() => {
    if (sortedSubsections && sortedSubsections.length > 0 && !selectedSubsectionId) {
      const first = sortedSubsections[0];
      setSelectedSubsection(first.id, {
        label: positionToLabel(first.position),
        title: first.title,
      });
    }
  }, [sortedSubsections, selectedSubsectionId, setSelectedSubsection]);

  // Reset subsection selection when section changes
  useEffect(() => {
    setSelectedSubsection(null);
  }, [selectedSectionId, setSelectedSubsection]);

  const subsectionHasValidConfig = (sub: { data_source_config: PreviewSubsection['data_source_config'] }) => {
    const config = sub.data_source_config;
    const inputs = config?.inputs || [];
    if (inputs.length === 0) return false;
    if (!dataSources || dataSources.length === 0) return true;

    for (const input of inputs) {
      const source = dataSources.find((item) => item.id === input.source_id);
      if (!source) return false;
      const method = source.retrieval_methods.find((item) => getMethodId(item) === input.method_id);
      if (!method) return false;
      const parameters = input.parameters || {};
      for (const parameter of method.parameters || []) {
        if (!parameter.required) continue;
        const key = parameter.key || parameter.name;
        if (!key) continue;
        if (isMissingValue((parameters as Record<string, unknown>)[key])) return false;
      }
    }
    return true;
  };

  const isSectionGenerating = selectedSectionId ? generatingSections.has(selectedSectionId) : false;
  const subsectionsWithInstructions = currentSection?.subsections.filter((sub) => sub.has_instructions) || [];
  const missingDataSourceCount = subsectionsWithInstructions.filter((sub) => !subsectionHasValidConfig(sub)).length;
  const canGenerateSection = subsectionsWithInstructions.length > 0 && missingDataSourceCount === 0;

  const handleSubsectionClick = (subsection: PreviewSubsection) => {
    setSelectedSubsection(subsection.id, {
      label: positionToLabel(subsection.position),
      title: subsection.title,
    });
  };

  const handleAddSubsection = async () => {
    if (!selectedSectionId) return;

    try {
      await createSubsection.mutateAsync({
        sectionId: selectedSectionId,
        templateId,
      });
      toast.success('Subsection added');
    } catch (err) {
      console.error('Failed to add subsection:', err);
      toast.error('Failed to add subsection');
    }
  };

  const handleDeleteSubsection = async (subsectionId: string) => {
    if (!window.confirm('Delete this subsection and all its content?')) return;

    try {
      await deleteSubsection.mutateAsync({
        subsectionId,
        templateId,
      });
      if (selectedSubsectionId === subsectionId) {
        setSelectedSubsection(null);
      }
      toast.success('Subsection deleted');
    } catch (err: unknown) {
      console.error('Failed to delete subsection:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete subsection';
      toast.error(errorMessage);
    }
  };

  const handleGenerateSection = async () => {
    if (!selectedSectionId || !currentSection) return;

    if (!canGenerateSection) {
      toast.error('Configure source, method, and required parameters for each subsection before running this section.');
      return;
    }

    try {
      setSectionGenerating(selectedSectionId, true);
      toast.info('Generating section content...');
      const result = await generateSection.mutateAsync(selectedSectionId);
      toast.success(`Generated ${result.generated_count} subsection${result.generated_count === 1 ? '' : 's'}!`);
    } catch (err) {
      console.error('Failed to generate section:', err);
      toast.error(getErrorMessage(err, 'Failed to generate section. Please try again.'));
    } finally {
      setSectionGenerating(selectedSectionId, false);
    }
  };

  if (!selectedSectionId) {
    return (
      <div className="flex-1 flex items-center justify-center rounded-xl border border-zinc-200 bg-gradient-to-b from-zinc-100/95 to-zinc-200/70 shadow-sm">
        <div className="text-center text-zinc-500">
          <svg className="w-16 h-16 mx-auto mb-4 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-lg font-medium">Select a section</p>
          <p className="text-sm mt-1">Choose a section from the sidebar to edit</p>
        </div>
      </div>
    );
  }

  if (!currentSection || !previewSection) {
    return (
      <div className="flex-1 flex items-center justify-center rounded-xl border border-zinc-200 bg-gradient-to-b from-zinc-100/95 to-zinc-200/70 shadow-sm">
        <div className="text-zinc-500">Loading section...</div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col rounded-xl border border-zinc-200 bg-gradient-to-b from-zinc-100/95 to-zinc-200/70 shadow-sm overflow-hidden">
      {/* Section header */}
      <div className="bg-white/90 backdrop-blur-sm border-b border-zinc-200/90 px-6 py-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-zinc-900">
            <span className="text-zinc-400 mr-2">{currentSection.position}.</span>
            {currentSection.title || 'Untitled Section'}
          </h2>
          <p className="text-sm text-zinc-500 mt-1">
            {sortedSubsections?.length || 0} subsection{(sortedSubsections?.length || 0) !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex items-center">
          <button
            onClick={handleGenerateSection}
            disabled={isSectionGenerating || generateSection.isPending}
            className={`h-10 w-10 inline-flex items-center justify-center rounded-lg border transition-colors ${
              canGenerateSection
                ? 'border-green-600 bg-green-600 text-white hover:bg-green-700'
                : 'border-green-300 bg-green-100 text-green-700 hover:bg-green-200'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
            title={
              canGenerateSection
                ? 'Generate all configured subsections in this section'
                : 'Configure data source, method, and required parameters for each subsection with instructions'
            }
            aria-label="Run section"
          >
            {isSectionGenerating || generateSection.isPending ? (
              <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.5 4.5v5h5M19.5 19.5v-5h-5M5.6 14a7 7 0 0011.8 2.1L19.5 14M18.4 10a7 7 0 00-11.8-2.1L4.5 10" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.5 4.5v5h5M19.5 19.5v-5h-5M5.6 14a7 7 0 0011.8 2.1L19.5 14M18.4 10a7 7 0 00-11.8-2.1L4.5 10" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Subsection list */}
      <div className="flex-1 overflow-auto p-6 bg-zinc-100/55">
        <div className="max-w-5xl mx-auto space-y-4">
          {/* Generating overlay */}
          {isSectionGenerating && (
            <div className="bg-sky-50 border border-sky-200 rounded-lg p-4 flex items-center gap-3 mb-4">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-sky-600" />
              <span className="text-sky-700">Generating content for all subsections...</span>
            </div>
          )}

          {/* Subsection cards with inline tabs/config */}
          {sortedSubsections?.map((subsection) => (
            <SubsectionWorkspace
              key={subsection.id}
              templateId={templateId}
              subsectionId={subsection.id}
              isActive={selectedSubsectionId === subsection.id}
              onActivate={() => handleSubsectionClick(subsection)}
              onDelete={sortedSubsections.length > 1 ? () => handleDeleteSubsection(subsection.id) : undefined}
            />
          ))}

          {/* Add subsection button */}
          <button
            onClick={handleAddSubsection}
            disabled={createSubsection.isPending}
            className="w-full py-4 border-2 border-dashed border-zinc-300 rounded-lg text-zinc-500 hover:border-sky-400 hover:text-sky-600 hover:bg-sky-50 transition-colors flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            {createSubsection.isPending ? 'Adding...' : 'Add Subsection'}
          </button>
        </div>
      </div>
    </div>
  );
}
