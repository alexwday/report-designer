import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import {
  useSections,
  useSubsection,
  useDataSourceRegistry,
  useConfigureSubsection,
  useUpdateNotes,
  useUpdateInstructions,
  useVersion,
  useGenerateSubsection,
} from '../api/queries';
import { useWorkspaceStore } from '../store/workspace';
import { Markdown } from './Markdown';
import { ChartRenderer } from './ChartRenderer';
import { positionToLabel } from '../api/types';
import type {
  DataInputConfig,
  DataSourceRegistry,
  ParameterDefinition,
  RetrievalMethod,
  VisualizationConfig,
  VersionSummary,
  WidgetType,
} from '../api/types';

function getMethodId(method: RetrievalMethod): string {
  return method.method_id || method.id || '';
}

function getParameterKey(parameter: ParameterDefinition): string {
  return parameter.key || parameter.name || '';
}

function getParameterLabel(parameter: ParameterDefinition, key: string): string {
  return parameter.prompt || parameter.description || key;
}

const VARIABLE_BINDING_KEY = '$var';
const VARIABLE_DEFAULT_KEY = '$default';
const PERIOD_BINDING_KEY = '$period';
const PERIOD_COUNT_KEY = '$count';

type TabKey = 'content' | 'instructions' | 'data';
type ParameterMode = 'fixed' | 'prompt' | 'dynamic';

const WIDGET_OPTIONS: Array<{ value: WidgetType; label: string }> = [
  { value: 'summary', label: 'Summary' },
  { value: 'key_points', label: 'Key points' },
  { value: 'table', label: 'Table' },
  { value: 'chart', label: 'Chart' },
  { value: 'comparison', label: 'Comparison' },
  { value: 'custom', label: 'Custom' },
];

function normalizeVisualizationConfig(visualization: VisualizationConfig | null | undefined): VisualizationConfig {
  if (!visualization) {
    return { chart_type: 'bar' };
  }
  return {
    chart_type: visualization.chart_type || 'bar',
    title: visualization.title,
    x_key: visualization.x_key,
    y_key: visualization.y_key,
    series_key: visualization.series_key,
    metric_id: visualization.metric_id,
  };
}

interface VariableBinding {
  $var: string;
  $default?: unknown;
}

interface PeriodBinding {
  $period: string;
  $count?: number;
}

interface InputReadiness {
  ready: boolean;
  issues: string[];
}

interface SourceStatus {
  sourceId: string;
  status: 'not_configured' | 'needs_input' | 'ready';
  inputIndices: number[];
}

function isVariableBindingCandidate(value: unknown): value is Record<string, unknown> {
  return (
    typeof value === 'object'
    && value !== null
    && !Array.isArray(value)
    && VARIABLE_BINDING_KEY in value
  );
}

function toVariableBinding(value: unknown): VariableBinding {
  if (!isVariableBindingCandidate(value)) {
    return { $var: '' };
  }
  const binding: VariableBinding = {
    $var: typeof value[VARIABLE_BINDING_KEY] === 'string' ? value[VARIABLE_BINDING_KEY] : '',
  };
  if (VARIABLE_DEFAULT_KEY in value) {
    binding.$default = value[VARIABLE_DEFAULT_KEY];
  }
  return binding;
}

function hasMissingVariableName(value: unknown): boolean {
  if (!isVariableBindingCandidate(value)) return false;
  return typeof value[VARIABLE_BINDING_KEY] !== 'string' || value[VARIABLE_BINDING_KEY].trim() === '';
}

function isPeriodBindingCandidate(value: unknown): value is Record<string, unknown> {
  return (
    typeof value === 'object'
    && value !== null
    && !Array.isArray(value)
    && PERIOD_BINDING_KEY in value
  );
}

function toPeriodBinding(value: unknown): PeriodBinding {
  if (!isPeriodBindingCandidate(value)) {
    return { $period: '' };
  }
  const binding: PeriodBinding = {
    $period: typeof value[PERIOD_BINDING_KEY] === 'string' ? value[PERIOD_BINDING_KEY] : '',
  };
  if (PERIOD_COUNT_KEY in value && typeof value[PERIOD_COUNT_KEY] === 'number') {
    binding.$count = value[PERIOD_COUNT_KEY];
  }
  return binding;
}

function hasMissingPeriodSelector(value: unknown): boolean {
  if (!isPeriodBindingCandidate(value)) return false;
  return typeof value[PERIOD_BINDING_KEY] !== 'string' || value[PERIOD_BINDING_KEY].trim() === '';
}

function getPeriodSelectorOptions(parameterType: string): Array<{ value: string; label: string }> {
  if (parameterType === 'integer') {
    return [
      { value: 'current.fiscal_year', label: 'Current fiscal year' },
      { value: 'qoq.fiscal_year', label: 'Previous quarter fiscal year' },
      { value: 'yoy.fiscal_year', label: 'Same quarter last year (fiscal year)' },
    ];
  }
  if (parameterType === 'enum' || parameterType === 'string') {
    return [
      { value: 'current.fiscal_quarter', label: 'Current fiscal quarter' },
      { value: 'qoq.fiscal_quarter', label: 'Previous fiscal quarter' },
      { value: 'yoy.fiscal_quarter', label: 'Same quarter last year (fiscal quarter)' },
    ];
  }
  if (parameterType === 'object') {
    return [
      { value: 'current', label: 'Current period object' },
      { value: 'qoq', label: 'Previous quarter period object' },
      { value: 'yoy', label: 'Same quarter last year period object' },
    ];
  }
  if (parameterType === 'array') {
    return [
      { value: 'trailing_quarters', label: 'Trailing quarters window' },
    ];
  }
  return [];
}

function getDefaultPeriodSelector(parameterType: string): string {
  if (parameterType === 'integer') return 'current.fiscal_year';
  if (parameterType === 'enum' || parameterType === 'string') return 'current.fiscal_quarter';
  if (parameterType === 'object') return 'current';
  if (parameterType === 'array') return 'trailing_quarters';
  return '';
}

function validatePeriodBindingForType(parameter: ParameterDefinition, value: unknown): string | null {
  if (!isPeriodBindingCandidate(value)) return 'Invalid dynamic value rule';
  const selector = typeof value[PERIOD_BINDING_KEY] === 'string' ? value[PERIOD_BINDING_KEY].trim() : '';
  if (!selector) return 'Dynamic rule is required';

  const parameterType = parameter.type.toLowerCase();
  const allowed = getPeriodSelectorOptions(parameterType).map((item) => item.value);
  if (allowed.length === 0) {
    return `Dynamic values are not supported for type '${parameterType}'`;
  }
  if (!allowed.includes(selector)) {
    return `Rule '${selector}' is not valid for type '${parameterType}'`;
  }

  if (selector === 'trailing_quarters') {
    const rawCount = value[PERIOD_COUNT_KEY];
    if (rawCount !== undefined) {
      if (typeof rawCount !== 'number' || !Number.isInteger(rawCount) || rawCount < 1) {
        return 'Trailing quarter count must be a positive integer';
      }
    }
  }

  return null;
}

function isMissingValue(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === 'string' && value.trim() === '') return true;
  if (Array.isArray(value) && value.length === 0) return true;
  if (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0) return true;
  return false;
}

function coerceParameterValue(
  parameter: ParameterDefinition,
  rawValue: unknown,
): { value?: unknown; error?: string } {
  const parameterType = parameter.type.toLowerCase();
  const parameterKey = getParameterKey(parameter) || 'parameter';

  if (parameterType === 'integer') {
    const parsed = typeof rawValue === 'number' ? rawValue : Number.parseInt(String(rawValue), 10);
    if (!Number.isInteger(parsed)) return { error: 'Must be an integer' };
    return { value: parsed };
  }

  if (parameterType === 'number') {
    const parsed = typeof rawValue === 'number' ? rawValue : Number.parseFloat(String(rawValue));
    if (Number.isNaN(parsed)) return { error: 'Must be a number' };
    return { value: parsed };
  }

  if (parameterType === 'boolean') {
    if (typeof rawValue === 'boolean') return { value: rawValue };
    const normalized = String(rawValue).trim().toLowerCase();
    if (normalized === 'true' || normalized === '1' || normalized === 'yes') return { value: true };
    if (normalized === 'false' || normalized === '0' || normalized === 'no') return { value: false };
    return { error: 'Must be true or false' };
  }

  if (parameterType === 'array') {
    let parsed = rawValue;
    if (!Array.isArray(rawValue)) {
      parsed = String(rawValue)
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean);
    }
    if (!Array.isArray(parsed)) return { error: 'Must be an array' };

    const arrayOptions = parameter.items?.options || parameter.items?.enum || [];
    if (arrayOptions.length > 0) {
      const invalid = parsed.filter((item) => !arrayOptions.includes(String(item)));
      if (invalid.length > 0) {
        return { error: `Invalid values: ${invalid.map(String).join(', ')}` };
      }
    }
    return { value: parsed };
  }

  if (parameterType === 'object') {
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

  const asString = String(rawValue).trim();
  if (parameterType === 'enum') {
    const options = parameter.options || parameter.enum || [];
    if (options.length > 0 && !options.includes(asString)) {
      return { error: `Must be one of: ${options.join(', ')}` };
    }
  }

  if (parameterType === 'string' && asString === '') {
    return { error: `Parameter '${parameterKey}' must be a string` };
  }

  return { value: asString };
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

function getParameterMode(parameterType: string, value: unknown): ParameterMode {
  if (isVariableBindingCandidate(value)) return 'prompt';
  if (isPeriodBindingCandidate(value) && getPeriodSelectorOptions(parameterType).length > 0) return 'dynamic';
  return 'fixed';
}

function evaluateInputReadiness(
  input: DataInputConfig,
  registry: DataSourceRegistry[] | undefined,
): InputReadiness {
  if (!input.source_id || !input.method_id) {
    return { ready: false, issues: ['Source and retrieval method are required'] };
  }

  if (!registry || registry.length === 0) {
    return { ready: true, issues: [] };
  }

  const source = registry.find((candidate) => candidate.id === input.source_id);
  if (!source) {
    return { ready: false, issues: ['Selected source no longer exists'] };
  }

  const method = source.retrieval_methods.find((candidate) => getMethodId(candidate) === input.method_id);
  if (!method) {
    return { ready: false, issues: ['Selected retrieval method no longer exists'] };
  }

  const parameters = input.parameters || {};
  const issues: string[] = [];

  for (const parameter of method.parameters || []) {
    if (!parameter.required) continue;
    const key = getParameterKey(parameter);
    if (!key) continue;
    const value = (parameters as Record<string, unknown>)[key];

    if (isMissingValue(value) || hasMissingVariableName(value) || hasMissingPeriodSelector(value)) {
      issues.push(`${key} is required`);
    }
  }

  return {
    ready: issues.length === 0,
    issues,
  };
}

function collectRuntimeInputKeys(inputs: DataInputConfig[]): string[] {
  const values = new Set<string>();
  for (const input of inputs) {
    const parameters = input.parameters || {};
    for (const value of Object.values(parameters)) {
      if (!isVariableBindingCandidate(value)) continue;
      const name = typeof value[VARIABLE_BINDING_KEY] === 'string' ? value[VARIABLE_BINDING_KEY].trim() : '';
      if (name) values.add(name);
    }
  }
  return Array.from(values).sort((a, b) => a.localeCompare(b));
}

interface SubsectionWorkspaceProps {
  templateId: string;
  subsectionId?: string;
  isActive?: boolean;
  onActivate?: () => void;
  onDelete?: () => void;
}

export function SubsectionWorkspace({
  templateId,
  subsectionId: subsectionIdProp,
  isActive = false,
  onActivate,
  onDelete,
}: SubsectionWorkspaceProps) {
  const {
    selectedSubsectionId,
    setSubsectionGenerating,
    generatingSubsections,
  } = useWorkspaceStore();

  const effectiveSubsectionId = subsectionIdProp ?? selectedSubsectionId;

  const { data: subsection, isLoading: subsectionLoading } = useSubsection(effectiveSubsectionId || '');
  const { data: dataSources } = useDataSourceRegistry();
  const { data: sections } = useSections(templateId);

  const configureSubsection = useConfigureSubsection();
  const updateNotes = useUpdateNotes();
  const updateInstructions = useUpdateInstructions();
  const generateSubsection = useGenerateSubsection(templateId);

  const [activeTab, setActiveTab] = useState<TabKey>('content');

  const [notes, setNotes] = useState('');
  const [instructions, setInstructions] = useState('');
  const [notesDirty, setNotesDirty] = useState(false);
  const [instructionsDirty, setInstructionsDirty] = useState(false);
  const [widgetType, setWidgetType] = useState<WidgetType>('summary');

  const [selectedSourceId, setSelectedSourceId] = useState<string>('');
  const [selectedMethodId, setSelectedMethodId] = useState<string>('');
  const [parameterValues, setParameterValues] = useState<Record<string, unknown>>({});
  const [parameterErrors, setParameterErrors] = useState<Record<string, string>>({});
  const [selectedInputIndex, setSelectedInputIndex] = useState<number | null>(null);
  const [dependencySectionIds, setDependencySectionIds] = useState<string[]>([]);
  const [dependencySubsectionIds, setDependencySubsectionIds] = useState<string[]>([]);
  const [visualizationConfig, setVisualizationConfig] = useState<VisualizationConfig>(
    normalizeVisualizationConfig(undefined)
  );
  const [dataDraftDirty, setDataDraftDirty] = useState(false);

  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);

  const { data: historicalVersion } = useVersion(selectedVersionId || '');
  const isViewingHistorical = selectedVersionId !== null && historicalVersion !== undefined;

  const configuredInputs = subsection?.data_source_config?.inputs || [];

  const loadInputDraft = useCallback((input: DataInputConfig, inputIndex: number) => {
    setSelectedInputIndex(inputIndex);
    setSelectedSourceId(input.source_id || '');
    setSelectedMethodId(input.method_id || '');
    setParameterValues(input.parameters || {});
    setParameterErrors({});
    setDataDraftDirty(false);
  }, []);

  useEffect(() => {
    if (subsection && !selectedVersionId) {
      setNotes(subsection.notes || '');
      setInstructions(subsection.instructions || '');
      setNotesDirty(false);
      setInstructionsDirty(false);
      setWidgetType((subsection.widget_type as WidgetType) || 'summary');

      if (subsection.data_source_config) {
        const dependencies = subsection.data_source_config.dependencies;
        setDependencySectionIds(dependencies?.section_ids || []);
        setDependencySubsectionIds(dependencies?.subsection_ids || []);
        setVisualizationConfig(
          normalizeVisualizationConfig(subsection.data_source_config.visualization || undefined)
        );

        const firstInput = subsection.data_source_config.inputs?.[0];
        if (firstInput) {
          loadInputDraft(firstInput, 0);
        } else {
          setSelectedInputIndex(null);
          setSelectedSourceId('');
          setSelectedMethodId('');
          setParameterValues({});
          setParameterErrors({});
          setVisualizationConfig(normalizeVisualizationConfig(undefined));
          setDataDraftDirty(false);
        }
      } else {
        setSelectedInputIndex(null);
        setSelectedSourceId('');
        setSelectedMethodId('');
        setParameterValues({});
        setParameterErrors({});
        setDependencySectionIds([]);
        setDependencySubsectionIds([]);
        setVisualizationConfig(normalizeVisualizationConfig(undefined));
        setDataDraftDirty(false);
      }
    }
  }, [subsection, selectedVersionId, loadInputDraft]);

  useEffect(() => {
    setSelectedVersionId(null);
    setActiveTab('content');
  }, [effectiveSubsectionId]);

  const selectedSource = useMemo(
    () => dataSources?.find((source) => source.id === selectedSourceId),
    [dataSources, selectedSourceId],
  );
  const methods = selectedSource?.retrieval_methods || [];
  const selectedMethod = methods.find((method) => getMethodId(method) === selectedMethodId);
  const methodParameters = selectedMethod?.parameters || [];

  const inputReadiness = useMemo(
    () => configuredInputs.map((input) => evaluateInputReadiness(input, dataSources)),
    [configuredInputs, dataSources],
  );

  const sourceStatuses = useMemo<SourceStatus[]>(() => {
    if (!dataSources) return [];

    return dataSources.map((source) => {
      const indices = configuredInputs
        .map((input, index) => ({ input, index }))
        .filter((entry) => entry.input.source_id === source.id)
        .map((entry) => entry.index);

      if (indices.length === 0) {
        return {
          sourceId: source.id,
          status: 'not_configured',
          inputIndices: [],
        };
      }

      const ready = indices.every((index) => inputReadiness[index]?.ready);
      return {
        sourceId: source.id,
        status: ready ? 'ready' : 'needs_input',
        inputIndices: indices,
      };
    });
  }, [configuredInputs, dataSources, inputReadiness]);

  const sourceStatusMap = useMemo(
    () => new Map(sourceStatuses.map((item) => [item.sourceId, item])),
    [sourceStatuses],
  );

  const selectedSourceIds = useMemo(() => {
    const ids = new Set<string>();
    for (const input of configuredInputs) {
      if (input.source_id) ids.add(input.source_id);
    }
    return ids;
  }, [configuredInputs]);

  const selectedSourceCount = selectedSourceIds.size;
  const readySourceCount = sourceStatuses.filter((item) => item.status === 'ready').length;
  const needsInputSourceCount = sourceStatuses.filter((item) => item.status === 'needs_input').length;

  const runtimeInputKeys = useMemo(
    () => collectRuntimeInputKeys(configuredInputs),
    [configuredInputs],
  );

  const hasDataSourceConfigured = configuredInputs.length > 0 && inputReadiness.every((entry) => entry.ready);

  const missingRequiredParameterKeys = methodParameters
    .filter((parameter) => parameter.required)
    .map((parameter) => getParameterKey(parameter))
    .filter((key) => key && (
      isMissingValue(parameterValues[key])
      || hasMissingVariableName(parameterValues[key])
      || hasMissingPeriodSelector(parameterValues[key])
    ));

  const canConfigureDataSource = Boolean(
    selectedSourceId
      && selectedMethodId
      && missingRequiredParameterKeys.length === 0
      && Object.keys(parameterErrors).length === 0,
  );

  const dataTabNeedsAttention = !hasDataSourceConfigured
    || Object.keys(parameterErrors).length > 0
    || (selectedSourceId !== '' && selectedMethodId !== '' && missingRequiredParameterKeys.length > 0);

  const dependencySectionOptions = sections || [];
  const dependencySubsectionOptions = (sections || []).flatMap((section) => (
    section.subsections.map((subsectionItem) => ({
      id: subsectionItem.id,
      sectionTitle: section.title || `Section ${section.position}`,
      subsectionTitle: subsectionItem.title || `Subsection ${positionToLabel(subsectionItem.position)}`,
      subsectionLabel: positionToLabel(subsectionItem.position),
    }))
  ));

  const handleNotesChange = (value: string) => {
    setNotes(value);
    setNotesDirty(value !== (subsection?.notes || ''));
  };

  const handleInstructionsChange = (value: string) => {
    setInstructions(value);
    setInstructionsDirty(value !== (subsection?.instructions || ''));
  };

  const handleWidgetTypeChange = async (nextWidgetType: WidgetType) => {
    if (!effectiveSubsectionId || nextWidgetType === widgetType) return;
    setWidgetType(nextWidgetType);
    try {
      await configureSubsection.mutateAsync({
        subsectionId: effectiveSubsectionId,
        widget_type: nextWidgetType,
      });
      toast.success('Widget updated');
    } catch (err) {
      console.error('Failed to update widget type:', err);
      toast.error(getErrorMessage(err, 'Failed to update widget type'));
    }
  };

  const handleVisualizationChange = <K extends keyof VisualizationConfig>(
    key: K,
    value: VisualizationConfig[K]
  ) => {
    setVisualizationConfig((previous) => ({ ...previous, [key]: value }));
    setDataDraftDirty(true);
  };

  const buildVisualizationForSubmit = useCallback((): VisualizationConfig | undefined => {
    if (widgetType !== 'chart') return undefined;
    const normalized = normalizeVisualizationConfig(visualizationConfig);
    const visualization: VisualizationConfig = {
      chart_type: normalized.chart_type || 'bar',
    };
    if (normalized.title && normalized.title.trim()) visualization.title = normalized.title.trim();
    if (normalized.x_key && normalized.x_key.trim()) visualization.x_key = normalized.x_key.trim();
    if (normalized.y_key && normalized.y_key.trim()) visualization.y_key = normalized.y_key.trim();
    if (normalized.series_key && normalized.series_key.trim()) visualization.series_key = normalized.series_key.trim();
    if (normalized.metric_id && normalized.metric_id.trim()) visualization.metric_id = normalized.metric_id.trim();
    return visualization;
  }, [visualizationConfig, widgetType]);

  const saveNotesIfDirty = useCallback(async (silent = false): Promise<boolean> => {
    if (!effectiveSubsectionId || !notesDirty) return true;
    try {
      await updateNotes.mutateAsync({ subsectionId: effectiveSubsectionId, notes });
      setNotesDirty(false);
      if (!silent) toast.success('Notes saved');
      return true;
    } catch (err) {
      console.error('Failed to save notes:', err);
      if (!silent) toast.error('Failed to save notes');
      return false;
    }
  }, [effectiveSubsectionId, notesDirty, notes, updateNotes]);

  const saveInstructionsIfDirty = useCallback(async (silent = false): Promise<boolean> => {
    if (!effectiveSubsectionId || !instructionsDirty) return true;
    try {
      await updateInstructions.mutateAsync({ subsectionId: effectiveSubsectionId, instructions });
      setInstructionsDirty(false);
      if (!silent) toast.success('Instructions saved');
      return true;
    } catch (err) {
      console.error('Failed to save instructions:', err);
      if (!silent) toast.error('Failed to save instructions');
      return false;
    }
  }, [effectiveSubsectionId, instructionsDirty, instructions, updateInstructions]);

  const handleSourceCardSelect = (sourceId: string) => {
    const existingIndex = configuredInputs.findIndex((input) => input.source_id === sourceId);

    if (existingIndex >= 0) {
      loadInputDraft(configuredInputs[existingIndex], existingIndex);
      return;
    }

    setSelectedInputIndex(null);
    setSelectedSourceId(sourceId);
    setSelectedMethodId('');
    setParameterValues({});
    setParameterErrors({});
    setDataDraftDirty(true);
  };

  const handleMethodChange = (methodId: string) => {
    setSelectedMethodId(methodId);

    const nextMethod = methods.find((method) => getMethodId(method) === methodId);
    if (!nextMethod) {
      setParameterValues({});
      setParameterErrors({});
      setDataDraftDirty(true);
      return;
    }

    const defaults: Record<string, unknown> = {};
    for (const parameter of nextMethod.parameters || []) {
      const key = getParameterKey(parameter);
      if (!key) continue;
      if (parameter.default !== undefined) {
        defaults[key] = parameter.default;
      }
    }

    setParameterValues(defaults);

    setParameterErrors({});
    setDataDraftDirty(true);
  };

  const handleParameterChange = (parameterKey: string, value: unknown) => {
    setParameterValues((prev) => ({ ...prev, [parameterKey]: value }));
    setParameterErrors((prev) => {
      const next = { ...prev };
      delete next[parameterKey];
      return next;
    });
    setDataDraftDirty(true);
  };

  const handleParameterModeChange = (
    parameterKey: string,
    parameterType: string,
    mode: ParameterMode,
  ) => {
    setParameterValues((prev) => {
      const current = prev[parameterKey];
      if (mode === 'prompt') {
        if (isVariableBindingCandidate(current)) {
          return prev;
        }
        const nextBinding: VariableBinding = { $var: '' };
        if (!isMissingValue(current)) {
          nextBinding.$default = current;
        }
        return { ...prev, [parameterKey]: nextBinding };
      }

      if (mode === 'dynamic') {
        if (isPeriodBindingCandidate(current)) {
          return prev;
        }
        const selector = getDefaultPeriodSelector(parameterType);
        const nextBinding: PeriodBinding = { $period: selector };
        if (selector === 'trailing_quarters') {
          nextBinding.$count = 4;
        }
        return { ...prev, [parameterKey]: nextBinding };
      }

      if (isVariableBindingCandidate(current)) {
        return {
          ...prev,
          [parameterKey]: VARIABLE_DEFAULT_KEY in current ? current[VARIABLE_DEFAULT_KEY] : '',
        };
      }
      if (isPeriodBindingCandidate(current)) {
        return {
          ...prev,
          [parameterKey]: '',
        };
      }
      return prev;
    });

    setParameterErrors((prev) => {
      const next = { ...prev };
      delete next[parameterKey];
      return next;
    });

    setDataDraftDirty(true);
  };

  const handleVariableNameChange = (parameterKey: string, variableName: string) => {
    setParameterValues((prev) => {
      const binding = toVariableBinding(prev[parameterKey]);
      return {
        ...prev,
        [parameterKey]: {
          ...binding,
          $var: variableName,
        },
      };
    });

    setParameterErrors((prev) => {
      const next = { ...prev };
      delete next[parameterKey];
      return next;
    });

    setDataDraftDirty(true);
  };

  const handleVariableDefaultChange = (parameterKey: string, defaultValue: unknown) => {
    setParameterValues((prev) => {
      const binding = toVariableBinding(prev[parameterKey]);
      const nextBinding: VariableBinding = {
        $var: binding.$var,
      };
      if (!isMissingValue(defaultValue)) {
        nextBinding.$default = defaultValue;
      }
      return {
        ...prev,
        [parameterKey]: nextBinding,
      };
    });

    setParameterErrors((prev) => {
      const next = { ...prev };
      delete next[parameterKey];
      return next;
    });

    setDataDraftDirty(true);
  };

  const handlePeriodSelectorChange = (parameterKey: string, selector: string) => {
    setParameterValues((prev) => {
      const binding = toPeriodBinding(prev[parameterKey]);
      const nextBinding: PeriodBinding = {
        $period: selector,
      };
      if (selector === 'trailing_quarters') {
        nextBinding.$count = typeof binding.$count === 'number' ? binding.$count : 4;
      }
      return {
        ...prev,
        [parameterKey]: nextBinding,
      };
    });

    setParameterErrors((prev) => {
      const next = { ...prev };
      delete next[parameterKey];
      return next;
    });

    setDataDraftDirty(true);
  };

  const handlePeriodCountChange = (parameterKey: string, countRaw: string) => {
    setParameterValues((prev) => {
      const binding = toPeriodBinding(prev[parameterKey]);
      const nextBinding: PeriodBinding = {
        $period: binding.$period,
      };
      if (countRaw.trim() !== '') {
        const parsed = Number.parseInt(countRaw, 10);
        if (!Number.isNaN(parsed)) {
          nextBinding.$count = parsed;
        }
      }
      return {
        ...prev,
        [parameterKey]: nextBinding,
      };
    });

    setParameterErrors((prev) => {
      const next = { ...prev };
      delete next[parameterKey];
      return next;
    });

    setDataDraftDirty(true);
  };

  const buildParametersForSubmit = useCallback((): Record<string, unknown> | null => {
    const nextErrors: Record<string, string> = {};
    const nextParameters: Record<string, unknown> = {};

    for (const parameter of methodParameters) {
      const parameterKey = getParameterKey(parameter);
      if (!parameterKey) continue;
      const rawValue = parameterValues[parameterKey];

      if (isPeriodBindingCandidate(rawValue)) {
        const periodError = validatePeriodBindingForType(parameter, rawValue);
        if (periodError) {
          nextErrors[parameterKey] = periodError;
          continue;
        }
        const selector = String(rawValue[PERIOD_BINDING_KEY]).trim();
        const periodBinding: PeriodBinding = { $period: selector };
        if (selector === 'trailing_quarters' && typeof rawValue[PERIOD_COUNT_KEY] === 'number') {
          periodBinding.$count = rawValue[PERIOD_COUNT_KEY];
        }
        nextParameters[parameterKey] = periodBinding;
        continue;
      }

      if (isVariableBindingCandidate(rawValue)) {
        const variableNameRaw = rawValue[VARIABLE_BINDING_KEY];
        const variableName = typeof variableNameRaw === 'string' ? variableNameRaw.trim() : '';
        if (!variableName) {
          nextErrors[parameterKey] = 'Run-time input key is required';
          continue;
        }

        const variableBinding: VariableBinding = { $var: variableName };
        if (VARIABLE_DEFAULT_KEY in rawValue && !isMissingValue(rawValue[VARIABLE_DEFAULT_KEY])) {
          const defaultResult = coerceParameterValue(parameter, rawValue[VARIABLE_DEFAULT_KEY]);
          if (defaultResult.error) {
            nextErrors[parameterKey] = `Default value: ${defaultResult.error}`;
            continue;
          }
          variableBinding.$default = defaultResult.value;
        }

        nextParameters[parameterKey] = variableBinding;
        continue;
      }

      if (isMissingValue(rawValue)) {
        if (parameter.required) {
          nextErrors[parameterKey] = 'Required parameter';
        }
        continue;
      }

      const result = coerceParameterValue(parameter, rawValue);
      if (result.error) {
        nextErrors[parameterKey] = result.error;
        continue;
      }
      nextParameters[parameterKey] = result.value;
    }

    setParameterErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return null;
    }

    return nextParameters;
  }, [methodParameters, parameterValues]);

  const buildDependenciesForSubmit = useCallback((): {
    section_ids?: string[];
    subsection_ids?: string[];
  } | undefined => {
    const sectionIds = dependencySectionIds
      .map((id) => id.trim())
      .filter((id) => id.length > 0);
    const subsectionIds = dependencySubsectionIds
      .map((id) => id.trim())
      .filter((id) => id.length > 0);

    const dependencies: { section_ids?: string[]; subsection_ids?: string[] } = {};
    if (sectionIds.length > 0) dependencies.section_ids = sectionIds;
    if (subsectionIds.length > 0) dependencies.subsection_ids = subsectionIds;

    return Object.keys(dependencies).length > 0 ? dependencies : undefined;
  }, [dependencySectionIds, dependencySubsectionIds]);

  const saveDataInput = useCallback(async (silent = false): Promise<boolean> => {
    if (!effectiveSubsectionId || !selectedSourceId || !selectedMethodId) return false;

    const parameters = buildParametersForSubmit();
    if (parameters === null) {
      if (!silent) toast.error('Please fix parameter errors before saving.');
      return false;
    }

    try {
      const existingInputs = subsection?.data_source_config?.inputs || [];
      const nextInput: DataInputConfig = {
        source_id: selectedSourceId,
        method_id: selectedMethodId,
        parameters: Object.keys(parameters).length > 0 ? parameters : undefined,
      };

      let nextInputs: DataInputConfig[];
      let persistedIndex = selectedInputIndex;

      if (selectedInputIndex !== null && selectedInputIndex >= 0 && selectedInputIndex < existingInputs.length) {
        nextInputs = existingInputs.map((input, index) => (
          index === selectedInputIndex ? nextInput : input
        ));
      } else {
        nextInputs = [...existingInputs, nextInput];
        persistedIndex = nextInputs.length - 1;
      }

      await configureSubsection.mutateAsync({
        subsectionId: effectiveSubsectionId,
        data_source_config: {
          inputs: nextInputs,
          dependencies: buildDependenciesForSubmit(),
          visualization: buildVisualizationForSubmit(),
        },
      });

      if (persistedIndex !== null && persistedIndex >= 0) {
        setSelectedInputIndex(persistedIndex);
      }
      setDataDraftDirty(false);
      if (!silent) toast.success('Data source saved');
      return true;
    } catch (err) {
      console.error('Failed to save data source:', err);
      if (!silent) toast.error(getErrorMessage(err, 'Failed to save data source'));
      return false;
    }
  }, [
    effectiveSubsectionId,
    selectedSourceId,
    selectedMethodId,
    selectedInputIndex,
    subsection,
    buildDependenciesForSubmit,
    buildVisualizationForSubmit,
    buildParametersForSubmit,
    configureSubsection,
  ]);

  const saveDependencies = useCallback(async (silent = false): Promise<boolean> => {
    if (!effectiveSubsectionId || !subsection?.data_source_config) return false;
    const existingInputs = subsection.data_source_config.inputs || [];
    if (existingInputs.length === 0) return false;

    try {
      await configureSubsection.mutateAsync({
        subsectionId: effectiveSubsectionId,
        data_source_config: {
          inputs: existingInputs,
          dependencies: buildDependenciesForSubmit(),
          visualization: buildVisualizationForSubmit(),
        },
      });
      setDataDraftDirty(false);
      if (!silent) toast.success('Dependencies saved');
      return true;
    } catch (err) {
      console.error('Failed to save dependencies:', err);
      if (!silent) toast.error(getErrorMessage(err, 'Failed to save dependencies'));
      return false;
    }
  }, [effectiveSubsectionId, subsection, configureSubsection, buildDependenciesForSubmit, buildVisualizationForSubmit]);

  const persistDataDraft = useCallback(async (silent = false): Promise<boolean> => {
    if (!dataDraftDirty) return true;

    if (selectedSourceId && selectedMethodId) {
      return saveDataInput(silent);
    }

    if (configuredInputs.length > 0) {
      return saveDependencies(silent);
    }

    return false;
  }, [dataDraftDirty, selectedSourceId, selectedMethodId, configuredInputs.length, saveDataInput, saveDependencies]);

  const handleRemoveDataInput = async (inputIndex: number) => {
    if (!effectiveSubsectionId || !subsection?.data_source_config) return;

    const existingInputs = subsection.data_source_config.inputs || [];
    if (inputIndex < 0 || inputIndex >= existingInputs.length) return;

    const nextInputs = existingInputs.filter((_input, index) => index !== inputIndex);

    try {
      if (nextInputs.length === 0) {
        await configureSubsection.mutateAsync({
          subsectionId: effectiveSubsectionId,
          data_source_config: null,
        });
        setSelectedInputIndex(null);
        setSelectedSourceId('');
        setSelectedMethodId('');
        setParameterValues({});
        setParameterErrors({});
        setDependencySectionIds([]);
        setDependencySubsectionIds([]);
        setVisualizationConfig(normalizeVisualizationConfig(undefined));
        setDataDraftDirty(false);
        toast.success('All data sources removed');
        return;
      }

      await configureSubsection.mutateAsync({
        subsectionId: effectiveSubsectionId,
        data_source_config: {
          inputs: nextInputs,
          dependencies: buildDependenciesForSubmit(),
          visualization: buildVisualizationForSubmit(),
        },
      });

      if (selectedInputIndex === inputIndex) {
        const nextIndex = Math.min(inputIndex, nextInputs.length - 1);
        loadInputDraft(nextInputs[nextIndex], nextIndex);
      } else if (selectedInputIndex !== null && selectedInputIndex > inputIndex) {
        setSelectedInputIndex(selectedInputIndex - 1);
      }

      setDataDraftDirty(false);
      toast.success('Data source removed');
    } catch (err) {
      console.error('Failed to remove data source:', err);
      toast.error(getErrorMessage(err, 'Failed to remove data source'));
    }
  };

  const handleClearDataSources = async () => {
    if (!effectiveSubsectionId) return;

    try {
      await configureSubsection.mutateAsync({
        subsectionId: effectiveSubsectionId,
        data_source_config: null,
      });
      setSelectedInputIndex(null);
      setSelectedSourceId('');
      setSelectedMethodId('');
      setParameterValues({});
      setParameterErrors({});
      setDependencySectionIds([]);
      setDependencySubsectionIds([]);
      setVisualizationConfig(normalizeVisualizationConfig(undefined));
      setDataDraftDirty(false);
      toast.success('Data source configuration cleared');
    } catch (err) {
      console.error('Failed to clear data source configuration:', err);
      toast.error(getErrorMessage(err, 'Failed to clear data source configuration'));
    }
  };

  const toggleDependencySection = (sectionId: string) => {
    setDependencySectionIds((previous) => (
      previous.includes(sectionId)
        ? previous.filter((candidate) => candidate !== sectionId)
        : [...previous, sectionId]
    ));
    setDataDraftDirty(true);
  };

  const toggleDependencySubsection = (subsectionId: string) => {
    setDependencySubsectionIds((previous) => (
      previous.includes(subsectionId)
        ? previous.filter((candidate) => candidate !== subsectionId)
        : [...previous, subsectionId]
    ));
    setDataDraftDirty(true);
  };

  const handleVersionChange = (versionId: string) => {
    const version = subsection?.versions?.find((item) => item.id === versionId);
    if (!version) return;
    if (version.version_number === subsection?.version_number) {
      setSelectedVersionId(null);
    } else {
      setSelectedVersionId(versionId);
    }
  };

  const handleGenerateSubsection = async () => {
    if (!effectiveSubsectionId || !subsection) return;

    if (widgetType !== 'chart' && !instructions.trim()) {
      setActiveTab('instructions');
      toast.error('Add instructions before running this subsection.');
      return;
    }

    if (!hasDataSourceConfigured) {
      setActiveTab('data');
      toast.error('Finish data source setup before running this subsection.');
      return;
    }

    try {
      setSubsectionGenerating(effectiveSubsectionId, true);
      toast.info('Generating subsection content...');
      await generateSubsection.mutateAsync(effectiveSubsectionId);
      toast.success('Subsection generation complete');
    } catch (err) {
      console.error('Failed to generate subsection:', err);
      toast.error(getErrorMessage(err, 'Failed to generate subsection content.'));
    } finally {
      setSubsectionGenerating(effectiveSubsectionId, false);
    }
  };

  const isSubsectionGenerating = effectiveSubsectionId
    ? generatingSubsections.has(effectiveSubsectionId) || generateSubsection.isPending
    : false;

  const saveEverythingBeforeSwitch = useCallback(async () => {
    await Promise.all([
      saveInstructionsIfDirty(true),
      saveNotesIfDirty(true),
    ]);

    if (activeTab === 'data') {
      await persistDataDraft(true);
    }
  }, [activeTab, saveInstructionsIfDirty, saveNotesIfDirty, persistDataDraft]);

  const handleTabChange = (nextTab: TabKey) => {
    if (nextTab === activeTab) return;
    void saveEverythingBeforeSwitch();
    setActiveTab(nextTab);
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 's') {
        event.preventDefault();
        if (activeTab === 'instructions') {
          void Promise.all([
            saveInstructionsIfDirty(false),
            saveNotesIfDirty(false),
          ]);
          return;
        }
        void persistDataDraft(false);
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [activeTab, saveInstructionsIfDirty, saveNotesIfDirty, persistDataDraft]);

  if (!effectiveSubsectionId) {
    return (
      <div className="bg-white rounded-xl border border-zinc-200 p-8 text-center text-zinc-500">
        <svg className="w-12 h-12 mx-auto mb-3 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p className="text-sm">Select a subsection to configure content, instructions, and data sources.</p>
      </div>
    );
  }

  if (subsectionLoading || !subsection) {
    return (
      <div className="bg-white rounded-xl border border-zinc-200 p-8 text-center text-zinc-500">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-sky-600 mx-auto mb-3" />
        <p className="text-sm">Loading subsection workspace...</p>
      </div>
    );
  }

  const subsectionLabel = positionToLabel(subsection.position);
  const displayTitle = subsection.title || `Subsection ${subsectionLabel}`;
  const contentPreview = isViewingHistorical
    ? (historicalVersion?.content || '')
    : (subsection.content || '');
  const contentPreviewType = isViewingHistorical
    ? (historicalVersion?.content_type || subsection.content_type || 'markdown')
    : (subsection.content_type || 'markdown');
  const hasContentPreview = contentPreview.trim().length > 0;
  const instructionsTabDirty = instructionsDirty || notesDirty;
  const dataTabDirty = dataDraftDirty;

  return (
    <div
      className={`bg-white rounded-xl border overflow-hidden shadow-sm ${isActive ? 'border-sky-400 ring-2 ring-sky-200' : 'border-zinc-200'}`}
      onClick={onActivate}
    >
      <div className="px-5 py-4 border-b border-zinc-200 bg-zinc-50 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 className="text-base font-semibold text-zinc-900">
            <span className="text-sky-600 mr-2">{subsectionLabel}.</span>
            {displayTitle}
          </h3>
          <p className="text-xs text-zinc-500 mt-1">
            {hasDataSourceConfigured
              ? 'Data source configuration complete'
              : 'Data source setup still needs attention'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={widgetType}
            onChange={(event) => {
              event.stopPropagation();
              void handleWidgetTypeChange(event.target.value as WidgetType);
            }}
            onClick={(event) => event.stopPropagation()}
            className="px-2.5 py-2 text-sm border border-zinc-300 rounded-lg bg-white text-zinc-700 focus:outline-none focus:ring-2 focus:ring-sky-500"
            title="Select subsection widget type"
          >
            {WIDGET_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          {onDelete && (
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onDelete();
              }}
              className="px-3 py-2 text-sm border border-zinc-300 text-zinc-600 rounded-lg hover:bg-zinc-100"
              title="Delete subsection"
            >
              Delete
            </button>
          )}
          <button
            onClick={(event) => {
              event.stopPropagation();
              void handleGenerateSubsection();
            }}
            disabled={isSubsectionGenerating}
            className={`px-4 py-2 text-sm rounded-lg transition-colors flex items-center justify-center gap-2 ${
              hasDataSourceConfigured
                ? 'bg-green-600 text-white hover:bg-green-700'
                : 'bg-amber-100 text-amber-800 hover:bg-amber-200'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
            title={
              hasDataSourceConfigured
                ? 'Run generation for this subsection'
                : 'Open Data Sources tab and complete setup before running'
            }
          >
            {isSubsectionGenerating ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current" />
                Running...
              </>
            ) : hasDataSourceConfigured ? (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Run subsection
              </>
            ) : (
              'Finish data source setup'
            )}
          </button>
        </div>
      </div>

      <div className="px-5 border-b border-zinc-200 bg-white">
        <nav className="flex gap-3 overflow-x-auto">
          <TabButton
            label="Content"
            isActive={activeTab === 'content'}
            onClick={() => handleTabChange('content')}
          />
          <TabButton
            label="Instructions & Notes"
            isActive={activeTab === 'instructions'}
            showDirty={instructionsTabDirty}
            onClick={() => handleTabChange('instructions')}
          />
          <TabButton
            label="Data Sources"
            isActive={activeTab === 'data'}
            showDirty={dataTabDirty}
            showIssue={dataTabNeedsAttention}
            onClick={() => handleTabChange('data')}
          />
        </nav>
      </div>

      <div className="p-5">
        {activeTab === 'content' && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2 justify-between">
              <div className="text-xs text-zinc-500">
                Generated content preview for this subsection.
              </div>
              <div className="flex items-center gap-2">
                {subsection?.versions && subsection.versions.length > 0 && (
                  <select
                    className="text-xs border border-zinc-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-sky-500"
                    value={selectedVersionId || subsection.versions.find((item) => item.version_number === subsection.version_number)?.id || ''}
                    onChange={(event) => handleVersionChange(event.target.value)}
                  >
                    {subsection.versions.map((version: VersionSummary) => (
                      <option key={version.id} value={version.id}>
                        v{version.version_number}{version.version_number === subsection.version_number ? ' (current)' : ''}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            {isViewingHistorical && (
              <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 px-3 py-2 rounded">
                Viewing historical generated output.
              </div>
            )}

            <div className="min-h-[260px] border border-zinc-200 rounded-lg bg-zinc-50 p-4">
              {hasContentPreview ? (
                contentPreviewType === 'markdown' || !contentPreviewType ? (
                  <Markdown content={contentPreview} className="prose prose-sm max-w-none text-zinc-800" />
                ) : contentPreviewType === 'json' ? (
                  <ChartRenderer content={contentPreview} />
                ) : (
                  <pre className="text-sm whitespace-pre-wrap text-zinc-700">{contentPreview}</pre>
                )
              ) : (
                <div className="h-full min-h-[220px] flex items-center justify-center text-center text-zinc-500">
                  <div>
                    <p className="text-sm font-medium">No generated content yet</p>
                    <p className="text-xs mt-1">Configure inputs, then click \"Run subsection\" to generate this preview.</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'instructions' && (
          <div className="space-y-4">
            <div className="text-xs text-zinc-500">
              Use this tab for author guidance and internal notes. These notes are not automatically included in output.
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Author instructions</label>
                <button
                  onClick={() => void saveInstructionsIfDirty(false)}
                  disabled={updateInstructions.isPending || !instructionsDirty}
                  className="px-3 py-1.5 text-xs bg-sky-600 text-white rounded hover:bg-sky-700 disabled:opacity-50"
                >
                  {updateInstructions.isPending ? 'Saving...' : 'Save instructions'}
                </button>
              </div>
              <textarea
                value={instructions}
                onChange={(event) => handleInstructionsChange(event.target.value)}
                placeholder="How should this subsection be generated?"
                className="w-full min-h-[150px] px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 resize-y"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Reviewer notes</label>
                <button
                  onClick={() => void saveNotesIfDirty(false)}
                  disabled={updateNotes.isPending || !notesDirty}
                  className="px-3 py-1.5 text-xs bg-sky-600 text-white rounded hover:bg-sky-700 disabled:opacity-50"
                >
                  {updateNotes.isPending ? 'Saving...' : 'Save notes'}
                </button>
              </div>
              <textarea
                value={notes}
                onChange={(event) => handleNotesChange(event.target.value)}
                placeholder="Internal notes for reviewers or operators..."
                className="w-full min-h-[130px] px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 resize-y"
              />
            </div>
          </div>
        )}

        {activeTab === 'data' && (
          <div className="space-y-5">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <SummaryStat label="Sources selected" value={String(selectedSourceCount)} />
              <SummaryStat label="Ready" value={String(readySourceCount)} tone="green" />
              <SummaryStat label="Needs input" value={String(needsInputSourceCount)} tone={needsInputSourceCount > 0 ? 'amber' : 'zinc'} />
              <SummaryStat label="Run-time inputs" value={String(runtimeInputKeys.length)} />
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-semibold text-zinc-900">1. Select data sources</h4>
                {configuredInputs.length > 0 && (
                  <button
                    onClick={handleClearDataSources}
                    className="text-xs text-red-600 hover:text-red-700"
                  >
                    Clear all
                  </button>
                )}
              </div>
              <p className="text-xs text-zinc-500 mb-3">
                Pick one or more sources. Each source can be configured with fixed, dynamic, or run-time values.
              </p>

              {dataSources && dataSources.length > 0 ? (
                <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                  {dataSources.map((source) => {
                    const status = sourceStatusMap.get(source.id)?.status || 'not_configured';
                    const isSelectedSource = selectedSourceId === source.id;

                    return (
                      <button
                        key={source.id}
                        type="button"
                        onClick={() => handleSourceCardSelect(source.id)}
                        className={`text-left p-3 rounded-lg border transition-colors ${
                          isSelectedSource
                            ? 'border-sky-500 bg-sky-50'
                            : 'border-zinc-200 bg-white hover:border-zinc-300 hover:bg-zinc-50'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-medium text-zinc-900">{source.name}</p>
                          <SourceBadge status={status} />
                        </div>
                        <p className="text-xs text-zinc-500 mt-1">{source.category}</p>
                        <p className="text-xs text-zinc-500 mt-1 line-clamp-2">{source.description}</p>
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div className="p-4 border border-zinc-200 rounded-lg text-sm text-zinc-500">
                  No active data sources are available.
                </div>
              )}
            </div>

            {configuredInputs.length > 0 && (
              <div className="rounded-lg border border-zinc-200">
                <div className="px-3 py-2 border-b border-zinc-200 bg-zinc-50 flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-zinc-900">Configured sources</h4>
                  <span className="text-xs text-zinc-500">{configuredInputs.length} configured</span>
                </div>
                <div className="divide-y divide-zinc-100">
                  {configuredInputs.map((input, index) => {
                    const inputSource = dataSources?.find((source) => source.id === input.source_id);
                    const inputMethod = inputSource?.retrieval_methods.find((method) => getMethodId(method) === input.method_id);
                    const readiness = inputReadiness[index];

                    return (
                      <div key={`${input.source_id}-${input.method_id}-${index}`} className="px-3 py-2 flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm text-zinc-900">{inputSource?.name || input.source_id}</p>
                          <p className="text-xs text-zinc-500">{inputMethod?.name || input.method_id}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            readiness?.ready
                              ? 'bg-green-100 text-green-700'
                              : 'bg-amber-100 text-amber-700'
                          }`}>
                            {readiness?.ready ? 'Ready' : 'Needs input'}
                          </span>
                          <button
                            onClick={() => loadInputDraft(input, index)}
                            className="text-xs text-sky-600 hover:text-sky-700"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => void handleRemoveDataInput(index)}
                            className="text-xs text-red-600 hover:text-red-700"
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {selectedSourceId && (
              <div className="rounded-lg border border-zinc-200 p-4 space-y-3">
                <div>
                  <h4 className="text-sm font-semibold text-zinc-900">2. Configure source parameters</h4>
                  <p className="text-xs text-zinc-500 mt-1">
                    Dynamic values update automatically quarter over quarter. Ask each run prompts for input every run.
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-600 mb-1">Retrieval method</label>
                  <select
                    value={selectedMethodId}
                    onChange={(event) => handleMethodChange(event.target.value)}
                    className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                  >
                    <option value="">Select a method...</option>
                    {methods.map((method) => (
                      <option key={getMethodId(method)} value={getMethodId(method)}>
                        {method.name}
                      </option>
                    ))}
                  </select>
                </div>

                {selectedMethod && methodParameters.length > 0 && (
                  <div className="space-y-3">
                    {methodParameters.map((parameter) => {
                      const parameterKey = getParameterKey(parameter);
                      if (!parameterKey) return null;

                      const label = getParameterLabel(parameter, parameterKey);
                      const parameterType = parameter.type.toLowerCase();
                      const value = parameterValues[parameterKey];
                      const options = parameter.options || parameter.enum || [];
                      const arrayItemOptions = parameter.items?.options || parameter.items?.enum || [];
                      const periodOptions = getPeriodSelectorOptions(parameterType);
                      const supportsDynamicMode = periodOptions.length > 0;

                      const mode = getParameterMode(parameterType, value);
                      const variableBinding = mode === 'prompt' ? toVariableBinding(value) : null;
                      const variableName = variableBinding?.$var || '';
                      const variableDefault = variableBinding?.$default;
                      const periodBinding = mode === 'dynamic' ? toPeriodBinding(value) : null;
                      const periodSelector = periodBinding?.$period || '';
                      const periodCount = periodBinding?.$count;

                      return (
                        <div key={parameterKey} className="rounded-lg border border-zinc-200 p-3">
                          <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                            <label className="text-sm text-zinc-800">
                              {label}
                              {parameter.required && <span className="text-red-500"> *</span>}
                            </label>
                            <div className="inline-flex rounded-lg border border-zinc-200 overflow-hidden">
                              <button
                                type="button"
                                onClick={() => handleParameterModeChange(parameterKey, parameterType, 'fixed')}
                                className={`px-2.5 py-1 text-xs ${
                                  mode === 'fixed' ? 'bg-sky-100 text-sky-700' : 'bg-white text-zinc-600 hover:bg-zinc-50'
                                }`}
                              >
                                Fixed
                              </button>
                              {supportsDynamicMode && (
                                <button
                                  type="button"
                                  onClick={() => handleParameterModeChange(parameterKey, parameterType, 'dynamic')}
                                  className={`px-2.5 py-1 text-xs border-l border-zinc-200 ${
                                    mode === 'dynamic' ? 'bg-sky-100 text-sky-700' : 'bg-white text-zinc-600 hover:bg-zinc-50'
                                  }`}
                                >
                                  Dynamic
                                </button>
                              )}
                              <button
                                type="button"
                                onClick={() => handleParameterModeChange(parameterKey, parameterType, 'prompt')}
                                className={`px-2.5 py-1 text-xs border-l border-zinc-200 ${
                                  mode === 'prompt' ? 'bg-sky-100 text-sky-700' : 'bg-white text-zinc-600 hover:bg-zinc-50'
                                }`}
                              >
                                Ask each run
                              </button>
                            </div>
                          </div>

                          <p className="text-[11px] text-zinc-500 mb-2">
                            {mode === 'fixed' && 'Use the same value for every run.'}
                            {mode === 'dynamic' && 'Dynamic values auto-update each run (for example: previous fiscal quarter).'}
                            {mode === 'prompt' && 'Prompt for this value each time the report runs.'}
                          </p>

                          {mode === 'prompt' ? (
                            <div className="space-y-2">
                              <input
                                type="text"
                                value={variableName}
                                onChange={(event) => handleVariableNameChange(parameterKey, event.target.value)}
                                placeholder="Run-time input key (example: fiscal_quarter)"
                                className="w-full px-2.5 py-2 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500 font-mono"
                              />

                              <div>
                                <label className="block text-[11px] text-zinc-500 mb-1">Default (optional)</label>

                                {parameterType === 'enum' && (
                                  <select
                                    value={typeof variableDefault === 'string' ? variableDefault : ''}
                                    onChange={(event) => handleVariableDefaultChange(parameterKey, event.target.value)}
                                    className="w-full px-2.5 py-2 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
                                  >
                                    <option value="">No default</option>
                                    {options.map((option) => (
                                      <option key={option} value={option}>{option}</option>
                                    ))}
                                  </select>
                                )}

                                {parameterType === 'boolean' && (
                                  <select
                                    value={
                                      variableDefault === true
                                        ? 'true'
                                        : variableDefault === false
                                          ? 'false'
                                          : ''
                                    }
                                    onChange={(event) => handleVariableDefaultChange(
                                      parameterKey,
                                      event.target.value === '' ? undefined : event.target.value === 'true',
                                    )}
                                    className="w-full px-2.5 py-2 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
                                  >
                                    <option value="">No default</option>
                                    <option value="true">True</option>
                                    <option value="false">False</option>
                                  </select>
                                )}

                                {parameterType === 'array' && arrayItemOptions.length > 0 && (
                                  <select
                                    multiple
                                    value={Array.isArray(variableDefault) ? variableDefault.map((item) => String(item)) : []}
                                    onChange={(event) => {
                                      const selected = Array.from(event.target.selectedOptions).map((option) => option.value);
                                      handleVariableDefaultChange(parameterKey, selected);
                                    }}
                                    className="w-full px-2.5 py-2 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500 h-24"
                                  >
                                    {arrayItemOptions.map((option) => (
                                      <option key={option} value={option}>{option}</option>
                                    ))}
                                  </select>
                                )}

                                {parameterType === 'object' && (
                                  <textarea
                                    value={
                                      typeof variableDefault === 'string'
                                        ? variableDefault
                                        : (variableDefault && typeof variableDefault === 'object' && !Array.isArray(variableDefault))
                                          ? JSON.stringify(variableDefault, null, 2)
                                          : ''
                                    }
                                    onChange={(event) => handleVariableDefaultChange(parameterKey, event.target.value)}
                                    placeholder='{"key":"value"}'
                                    className="w-full h-20 px-2.5 py-2 text-xs font-mono border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
                                  />
                                )}

                                {(
                                  parameterType === 'string'
                                  || parameterType === 'integer'
                                  || parameterType === 'number'
                                  || (parameterType === 'array' && arrayItemOptions.length === 0)
                                ) && (
                                  <input
                                    type={parameterType === 'integer' || parameterType === 'number' ? 'number' : 'text'}
                                    value={
                                      Array.isArray(variableDefault)
                                        ? variableDefault.map((item) => String(item)).join(', ')
                                        : variableDefault === undefined || variableDefault === null
                                          ? ''
                                          : String(variableDefault)
                                    }
                                    onChange={(event) => handleVariableDefaultChange(parameterKey, event.target.value)}
                                    placeholder={parameterType === 'array' ? 'Comma-separated values' : 'No default'}
                                    className="w-full px-2.5 py-2 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
                                  />
                                )}
                              </div>
                            </div>
                          ) : mode === 'dynamic' ? (
                            <div className="space-y-2">
                              <select
                                value={periodSelector}
                                onChange={(event) => handlePeriodSelectorChange(parameterKey, event.target.value)}
                                className="w-full px-2.5 py-2 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
                              >
                                <option value="">Select a dynamic rule...</option>
                                {periodOptions.map((option) => (
                                  <option key={option.value} value={option.value}>{option.label}</option>
                                ))}
                              </select>

                              {periodSelector === 'trailing_quarters' && (
                                <div>
                                  <label className="block text-[11px] text-zinc-500 mb-1">Number of trailing quarters</label>
                                  <input
                                    type="number"
                                    min={1}
                                    value={periodCount === undefined ? 4 : periodCount}
                                    onChange={(event) => handlePeriodCountChange(parameterKey, event.target.value)}
                                    className="w-full px-2.5 py-2 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
                                  />
                                </div>
                              )}
                            </div>
                          ) : (
                            <>
                              {parameterType === 'enum' && (
                                <select
                                  value={typeof value === 'string' ? value : ''}
                                  onChange={(event) => handleParameterChange(parameterKey, event.target.value)}
                                  className="w-full px-2.5 py-2 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
                                >
                                  <option value="">Select...</option>
                                  {options.map((option) => (
                                    <option key={option} value={option}>{option}</option>
                                  ))}
                                </select>
                              )}

                              {parameterType === 'boolean' && (
                                <label className="inline-flex items-center gap-2 text-sm text-zinc-700">
                                  <input
                                    type="checkbox"
                                    checked={Boolean(value)}
                                    onChange={(event) => handleParameterChange(parameterKey, event.target.checked)}
                                    className="rounded border-zinc-300 text-sky-600 focus:ring-sky-500"
                                  />
                                  Enabled
                                </label>
                              )}

                              {parameterType === 'array' && arrayItemOptions.length > 0 && (
                                <select
                                  multiple
                                  value={Array.isArray(value) ? value.map((item) => String(item)) : []}
                                  onChange={(event) => {
                                    const selected = Array.from(event.target.selectedOptions).map((option) => option.value);
                                    handleParameterChange(parameterKey, selected);
                                  }}
                                  className="w-full px-2.5 py-2 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500 h-24"
                                >
                                  {arrayItemOptions.map((option) => (
                                    <option key={option} value={option}>{option}</option>
                                  ))}
                                </select>
                              )}

                              {parameterType === 'object' && (
                                <textarea
                                  value={
                                    typeof value === 'string'
                                      ? value
                                      : (value && typeof value === 'object' && !Array.isArray(value))
                                        ? JSON.stringify(value, null, 2)
                                        : ''
                                  }
                                  onChange={(event) => handleParameterChange(parameterKey, event.target.value)}
                                  placeholder='{"key":"value"}'
                                  className="w-full h-20 px-2.5 py-2 text-xs font-mono border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
                                />
                              )}

                              {(
                                parameterType === 'string'
                                || parameterType === 'integer'
                                || parameterType === 'number'
                                || (parameterType === 'array' && arrayItemOptions.length === 0)
                              ) && (
                                <input
                                  type={parameterType === 'integer' || parameterType === 'number' ? 'number' : 'text'}
                                  value={
                                    Array.isArray(value)
                                      ? value.map((item) => String(item)).join(', ')
                                      : value === undefined || value === null
                                        ? ''
                                        : String(value)
                                  }
                                  onChange={(event) => handleParameterChange(parameterKey, event.target.value)}
                                  placeholder={parameterType === 'array' ? 'Comma-separated values' : ''}
                                  className="w-full px-2.5 py-2 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
                                />
                              )}
                            </>
                          )}

                          {parameterErrors[parameterKey] && (
                            <p className="text-xs text-red-600 mt-2">{parameterErrors[parameterKey]}</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {selectedSource && (
                  <p className="text-xs text-zinc-500">{selectedSource.description}</p>
                )}

                <div className="flex flex-wrap items-center gap-2">
                  {selectedSourceId && selectedMethodId && (
                    <button
                      onClick={() => void saveDataInput(false)}
                      disabled={configureSubsection.isPending || !canConfigureDataSource}
                      className="px-3 py-2 text-sm bg-sky-600 text-white rounded hover:bg-sky-700 disabled:opacity-50"
                    >
                      {configureSubsection.isPending
                        ? 'Saving...'
                        : selectedInputIndex !== null
                          ? 'Update data source'
                          : 'Add data source'}
                    </button>
                  )}
                  {selectedSourceId && selectedMethodId && missingRequiredParameterKeys.length > 0 && (
                    <p className="text-xs text-amber-700">Select a mode/value for all required parameters.</p>
                  )}
                </div>
              </div>
            )}

            {widgetType === 'chart' && (
              <div className="rounded-lg border border-zinc-200 p-4 space-y-3">
                <h4 className="text-sm font-semibold text-zinc-900">Chart visualization</h4>
                <p className="text-xs text-zinc-500">
                  These settings shape chart output when this subsection runs as a chart widget.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-zinc-600 mb-1">Chart type</label>
                    <select
                      value={visualizationConfig.chart_type || 'bar'}
                      onChange={(event) => handleVisualizationChange('chart_type', event.target.value as VisualizationConfig['chart_type'])}
                      className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    >
                      <option value="bar">Bar</option>
                      <option value="line">Line</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-zinc-600 mb-1">Chart title (optional)</label>
                    <input
                      type="text"
                      value={visualizationConfig.title || ''}
                      onChange={(event) => handleVisualizationChange('title', event.target.value)}
                      placeholder="e.g. Revenue comparison by bank"
                      className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-zinc-600 mb-1">Metric ID (optional)</label>
                    <input
                      type="text"
                      value={visualizationConfig.metric_id || ''}
                      onChange={(event) => handleVisualizationChange('metric_id', event.target.value)}
                      placeholder="e.g. total_revenue"
                      className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-zinc-600 mb-1">Y field key (optional)</label>
                    <input
                      type="text"
                      value={visualizationConfig.y_key || ''}
                      onChange={(event) => handleVisualizationChange('y_key', event.target.value)}
                      placeholder="e.g. close_price"
                      className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-zinc-600 mb-1">X field key (optional)</label>
                    <input
                      type="text"
                      value={visualizationConfig.x_key || ''}
                      onChange={(event) => handleVisualizationChange('x_key', event.target.value)}
                      placeholder="e.g. period"
                      className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-zinc-600 mb-1">Series field key (optional)</label>
                    <input
                      type="text"
                      value={visualizationConfig.series_key || ''}
                      onChange={(event) => handleVisualizationChange('series_key', event.target.value)}
                      placeholder="e.g. bank_id"
                      className="w-full px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                  </div>
                </div>
              </div>
            )}

            {(dependencySectionOptions.length > 0 || dependencySubsectionOptions.length > 0) && (
              <div className="rounded-lg border border-zinc-200 p-4 space-y-3">
                <h4 className="text-sm font-semibold text-zinc-900">Dependencies</h4>
                <p className="text-xs text-zinc-500">
                  Include context from related sections or subsections. This will be available during generation.
                </p>

                {dependencySectionOptions.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-zinc-600 mb-1">Sections</p>
                    <div className="space-y-1 max-h-32 overflow-y-auto rounded border border-zinc-100 p-2">
                      {dependencySectionOptions.map((section) => (
                        <label key={section.id} className="flex items-center gap-2 text-xs text-zinc-700">
                          <input
                            type="checkbox"
                            checked={dependencySectionIds.includes(section.id)}
                            onChange={() => toggleDependencySection(section.id)}
                            className="rounded border-zinc-300 text-sky-600 focus:ring-sky-500"
                          />
                          <span>{section.title || `Section ${section.position}`}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                {dependencySubsectionOptions.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-zinc-600 mb-1">Subsections</p>
                    <div className="space-y-1 max-h-40 overflow-y-auto rounded border border-zinc-100 p-2">
                      {dependencySubsectionOptions.map((option) => {
                          const isSelf = option.id === effectiveSubsectionId;
                        return (
                          <label
                            key={option.id}
                            className={`flex items-center gap-2 text-xs ${isSelf ? 'text-zinc-400' : 'text-zinc-700'}`}
                          >
                            <input
                              type="checkbox"
                              checked={dependencySubsectionIds.includes(option.id)}
                              onChange={() => toggleDependencySubsection(option.id)}
                              disabled={isSelf}
                              className="rounded border-zinc-300 text-sky-600 focus:ring-sky-500"
                            />
                            <span>
                              {option.sectionTitle} • {option.subsectionLabel}. {option.subsectionTitle}
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                )}

                <button
                  onClick={() => void saveDependencies(false)}
                  disabled={configureSubsection.isPending || configuredInputs.length === 0}
                  className="px-3 py-2 text-sm bg-zinc-100 text-zinc-700 rounded hover:bg-zinc-200 disabled:opacity-50"
                >
                  {configureSubsection.isPending ? 'Saving...' : 'Save dependencies'}
                </button>
              </div>
            )}

            <div className="rounded-lg border border-zinc-200 p-4">
              <h4 className="text-sm font-semibold text-zinc-900">3. Run-time input preview</h4>
              <p className="text-xs text-zinc-500 mt-1 mb-2">
                This subsection needs {runtimeInputKeys.length} value{runtimeInputKeys.length === 1 ? '' : 's'} at run time.
              </p>

              {runtimeInputKeys.length === 0 ? (
                <p className="text-xs text-zinc-500">No run-time prompts required for this subsection.</p>
              ) : (
                <ul className="space-y-1">
                  {runtimeInputKeys.map((key) => (
                    <li key={key} className="text-xs text-zinc-700 font-mono bg-zinc-50 border border-zinc-200 rounded px-2 py-1">
                      {key}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

interface TabButtonProps {
  label: string;
  isActive: boolean;
  showDirty?: boolean;
  showIssue?: boolean;
  onClick: () => void;
}

function TabButton({ label, isActive, showDirty = false, showIssue = false, onClick }: TabButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`relative px-1 py-3 text-sm border-b-2 transition-colors whitespace-nowrap ${
        isActive
          ? 'border-sky-600 text-sky-700 font-medium'
          : 'border-transparent text-zinc-500 hover:text-zinc-700'
      }`}
    >
      <span>{label}</span>
      {showDirty && (
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-500 ml-1.5 align-middle" title="Unsaved changes" />
      )}
      {showIssue && (
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-red-500 ml-1.5 align-middle" title="Needs attention" />
      )}
    </button>
  );
}

interface SummaryStatProps {
  label: string;
  value: string;
  tone?: 'zinc' | 'green' | 'amber';
}

function SummaryStat({ label, value, tone = 'zinc' }: SummaryStatProps) {
  const toneClass = tone === 'green'
    ? 'bg-green-50 border-green-200 text-green-700'
    : tone === 'amber'
      ? 'bg-amber-50 border-amber-200 text-amber-700'
      : 'bg-zinc-50 border-zinc-200 text-zinc-700';

  return (
    <div className={`rounded-lg border px-3 py-2 ${toneClass}`}>
      <p className="text-[11px] uppercase tracking-wide opacity-80">{label}</p>
      <p className="text-lg font-semibold leading-tight">{value}</p>
    </div>
  );
}

function SourceBadge({ status }: { status: SourceStatus['status'] }) {
  if (status === 'ready') {
    return <span className="text-[11px] px-2 py-0.5 rounded bg-green-100 text-green-700">Ready</span>;
  }
  if (status === 'needs_input') {
    return <span className="text-[11px] px-2 py-0.5 rounded bg-amber-100 text-amber-700">Needs input</span>;
  }
  return <span className="text-[11px] px-2 py-0.5 rounded bg-zinc-100 text-zinc-600">Not configured</span>;
}
