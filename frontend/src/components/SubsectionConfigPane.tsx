import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import {
  useSections,
  useSubsection,
  useDataSourceRegistry,
  useConfigureSubsection,
  useUpdateNotes,
  useUpdateInstructions,
  useSaveVersion,
  useVersion,
  useGenerateSubsection,
} from '../api/queries';
import { useWorkspaceStore } from '../store/workspace';
import { positionToLabel } from '../api/types';
import type { DataSourceRegistry, RetrievalMethod, ParameterDefinition, VersionSummary } from '../api/types';

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

interface VariableBinding {
  $var: string;
  $default?: unknown;
}

interface PeriodBinding {
  $period: string;
  $count?: number;
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
      { value: 'current.fiscal_year', label: 'Current Year' },
      { value: 'qoq.fiscal_year', label: 'QoQ Year (Last Quarter)' },
      { value: 'yoy.fiscal_year', label: 'YoY Year (Same Quarter Last Year)' },
    ];
  }
  if (parameterType === 'enum' || parameterType === 'string') {
    return [
      { value: 'current.fiscal_quarter', label: 'Current Quarter' },
      { value: 'qoq.fiscal_quarter', label: 'QoQ Quarter (Last Quarter)' },
      { value: 'yoy.fiscal_quarter', label: 'YoY Quarter (Same Quarter Last Year)' },
    ];
  }
  if (parameterType === 'object') {
    return [
      { value: 'current', label: 'Current Period' },
      { value: 'qoq', label: 'QoQ Period (Last Quarter)' },
      { value: 'yoy', label: 'YoY Period (Same Quarter Last Year)' },
    ];
  }
  if (parameterType === 'array') {
    return [
      { value: 'trailing_quarters', label: 'Trailing Quarters Window' },
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
  if (!isPeriodBindingCandidate(value)) return 'Invalid period binding';
  const selector = typeof value[PERIOD_BINDING_KEY] === 'string' ? value[PERIOD_BINDING_KEY].trim() : '';
  if (!selector) return 'Period selector is required';

  const parameterType = parameter.type.toLowerCase();
  const allowed = getPeriodSelectorOptions(parameterType).map((item) => item.value);
  if (allowed.length === 0) {
    return `Period binding is not supported for type '${parameterType}'`;
  }
  if (!allowed.includes(selector)) {
    return `Selector '${selector}' is not valid for type '${parameterType}'`;
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

interface SubsectionConfigPaneProps {
  templateId: string;
}

export function SubsectionConfigPane({ templateId }: SubsectionConfigPaneProps) {
  const {
    selectedSubsectionId,
    selectedSectionId,
    sidebarCollapsed,
    toggleSidebar,
    openMiniChat,
    setSubsectionGenerating,
    generatingSubsections
  } = useWorkspaceStore();

  const { data: subsection, isLoading: subsectionLoading } = useSubsection(selectedSubsectionId || '');
  const { data: dataSources } = useDataSourceRegistry();
  const { data: sections } = useSections(templateId);

  const configureSubsection = useConfigureSubsection();
  const updateNotes = useUpdateNotes();
  const updateInstructions = useUpdateInstructions();
  const saveVersion = useSaveVersion();
  const generateSubsection = useGenerateSubsection(templateId);

  // Local state
  const [notes, setNotes] = useState('');
  const [instructions, setInstructions] = useState('');
  const [content, setContent] = useState('');
  const [notesDirty, setNotesDirty] = useState(false);
  const [instructionsDirty, setInstructionsDirty] = useState(false);
  const [contentDirty, setContentDirty] = useState(false);
  const [selectedSourceId, setSelectedSourceId] = useState<string>('');
  const [selectedMethodId, setSelectedMethodId] = useState<string>('');
  const [parameterValues, setParameterValues] = useState<Record<string, unknown>>({});
  const [parameterErrors, setParameterErrors] = useState<Record<string, string>>({});
  const [dependencySectionIds, setDependencySectionIds] = useState<string[]>([]);
  const [dependencySubsectionIds, setDependencySubsectionIds] = useState<string[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);

  // Fetch historical version if selected
  const { data: historicalVersion } = useVersion(selectedVersionId || '');
  const isViewingHistorical = selectedVersionId !== null && historicalVersion !== undefined;

  // Sync with subsection data
  useEffect(() => {
    if (subsection && !selectedVersionId) {
      setNotes(subsection.notes || '');
      setInstructions(subsection.instructions || '');
      setContent(subsection.content || '');
      setNotesDirty(false);
      setInstructionsDirty(false);
      setContentDirty(false);
      if (subsection.data_source_config) {
        const firstInput = subsection.data_source_config.inputs?.[0];
        setSelectedSourceId(firstInput?.source_id || '');
        setSelectedMethodId(firstInput?.method_id || '');
        setParameterValues(firstInput?.parameters || {});
        setDependencySectionIds(subsection.data_source_config.dependencies?.section_ids || []);
        setDependencySubsectionIds(subsection.data_source_config.dependencies?.subsection_ids || []);
        setParameterErrors({});
      } else {
        setSelectedSourceId('');
        setSelectedMethodId('');
        setParameterValues({});
        setDependencySectionIds([]);
        setDependencySubsectionIds([]);
        setParameterErrors({});
      }
    }
  }, [subsection, selectedVersionId]);

  // Sync with historical version
  useEffect(() => {
    if (isViewingHistorical && historicalVersion) {
      setContent(historicalVersion.content || '');
      setInstructions(historicalVersion.instructions || '');
      setContentDirty(false);
      setInstructionsDirty(false);
    }
  }, [historicalVersion, isViewingHistorical]);

  // Reset version when switching subsections
  useEffect(() => {
    setSelectedVersionId(null);
  }, [selectedSubsectionId]);

  // Get selected source and its methods
  const selectedSource = dataSources?.find((ds: DataSourceRegistry) => ds.id === selectedSourceId);
  const methods = selectedSource?.retrieval_methods || [];
  const selectedMethod = methods.find((method) => getMethodId(method) === selectedMethodId);
  const methodParameters = selectedMethod?.parameters || [];

  // Handlers
  const handleNotesChange = (value: string) => {
    setNotes(value);
    setNotesDirty(value !== (subsection?.notes || ''));
  };

  const handleInstructionsChange = (value: string) => {
    setInstructions(value);
    setInstructionsDirty(value !== (subsection?.instructions || ''));
  };

  const handleContentChange = (value: string) => {
    setContent(value);
    setContentDirty(value !== (subsection?.content || ''));
  };

  const handleSaveNotes = useCallback(async () => {
    if (!selectedSubsectionId || !notesDirty) return;
    try {
      await updateNotes.mutateAsync({ subsectionId: selectedSubsectionId, notes });
      setNotesDirty(false);
      toast.success('Notes saved');
    } catch (err) {
      console.error('Failed to save notes:', err);
      toast.error('Failed to save notes');
    }
  }, [selectedSubsectionId, notesDirty, notes, updateNotes]);

  const handleSaveInstructions = useCallback(async () => {
    if (!selectedSubsectionId || !instructionsDirty) return;
    try {
      await updateInstructions.mutateAsync({ subsectionId: selectedSubsectionId, instructions });
      setInstructionsDirty(false);
      toast.success('Instructions saved');
    } catch (err) {
      console.error('Failed to save instructions:', err);
      toast.error('Failed to save instructions');
    }
  }, [selectedSubsectionId, instructionsDirty, instructions, updateInstructions]);

  const handleSaveContent = useCallback(async () => {
    if (!selectedSubsectionId || !contentDirty) return;
    try {
      await saveVersion.mutateAsync({
        subsectionId: selectedSubsectionId,
        templateId,
        content,
        content_type: 'markdown',
        generated_by: 'user_edit',
      });
      setContentDirty(false);
      toast.success('Content saved');
    } catch (err) {
      console.error('Failed to save content:', err);
      toast.error('Failed to save content');
    }
  }, [selectedSubsectionId, contentDirty, saveVersion, templateId, content]);

  const handleSourceChange = (sourceId: string) => {
    setSelectedSourceId(sourceId);
    setSelectedMethodId('');
    setParameterValues({});
    setParameterErrors({});
  };

  const handleMethodChange = (methodId: string) => {
    setSelectedMethodId(methodId);
    const nextMethod = methods.find((method) => getMethodId(method) === methodId);
    if (!nextMethod) {
      setParameterValues({});
      setParameterErrors({});
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
  };

  const handleParameterChange = (parameterKey: string, value: unknown) => {
    setParameterValues((prev) => ({ ...prev, [parameterKey]: value }));
    setParameterErrors((prev) => {
      const next = { ...prev };
      delete next[parameterKey];
      return next;
    });
  };

  const handleParameterModeChange = (
    parameterKey: string,
    parameterType: string,
    mode: 'literal' | 'variable' | 'period',
  ) => {
    setParameterValues((prev) => {
      const current = prev[parameterKey];
      if (mode === 'variable') {
        if (isVariableBindingCandidate(current)) {
          return prev;
        }
        const nextBinding: VariableBinding = { $var: '' };
        if (!isMissingValue(current)) {
          nextBinding.$default = current;
        }
        return { ...prev, [parameterKey]: nextBinding };
      }

      if (mode === 'period') {
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
  };

  const buildParametersForSubmit = () => {
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
          nextErrors[parameterKey] = 'Variable name is required';
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
  };

  const buildDependenciesForSubmit = (): {
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
  };

  const toggleDependencySection = (sectionId: string) => {
    setDependencySectionIds((previous) => (
      previous.includes(sectionId)
        ? previous.filter((candidate) => candidate !== sectionId)
        : [...previous, sectionId]
    ));
  };

  const toggleDependencySubsection = (subsectionId: string) => {
    setDependencySubsectionIds((previous) => (
      previous.includes(subsectionId)
        ? previous.filter((candidate) => candidate !== subsectionId)
        : [...previous, subsectionId]
    ));
  };

  const handleConfigureDataSource = async () => {
    if (!selectedSubsectionId || !selectedSourceId || !selectedMethodId) return;

    const parameters = buildParametersForSubmit();
    if (parameters === null) {
      toast.error('Please fix parameter errors before configuring.');
      return;
    }

    try {
      const existingInputs = subsection?.data_source_config?.inputs || [];
      const nextInputs = [
        ...existingInputs,
        {
          source_id: selectedSourceId,
          method_id: selectedMethodId,
          parameters: Object.keys(parameters).length > 0 ? parameters : undefined,
        },
      ];

      await configureSubsection.mutateAsync({
        subsectionId: selectedSubsectionId,
        data_source_config: {
          inputs: nextInputs,
          dependencies: buildDependenciesForSubmit(),
        },
      });
      toast.success('Data input added');
    } catch (err) {
      console.error('Failed to configure data source:', err);
      toast.error(getErrorMessage(err, 'Failed to configure data source'));
    }
  };

  const handleRemoveDataInput = async (inputIndex: number) => {
    if (!selectedSubsectionId || !subsection?.data_source_config) return;
    const existingInputs = subsection.data_source_config.inputs || [];
    if (inputIndex < 0 || inputIndex >= existingInputs.length) return;

    const nextInputs = existingInputs.filter((_input, index) => index !== inputIndex);
    try {
      if (nextInputs.length === 0) {
        await configureSubsection.mutateAsync({
          subsectionId: selectedSubsectionId,
          data_source_config: null,
        });
        toast.success('Data inputs cleared');
        return;
      }

      await configureSubsection.mutateAsync({
        subsectionId: selectedSubsectionId,
        data_source_config: {
          inputs: nextInputs,
          dependencies: buildDependenciesForSubmit(),
        },
      });
      toast.success('Data input removed');
    } catch (err) {
      console.error('Failed to remove data input:', err);
      toast.error(getErrorMessage(err, 'Failed to remove data input'));
    }
  };

  const handleSaveDependencies = async () => {
    if (!selectedSubsectionId || !subsection?.data_source_config) return;
    const existingInputs = subsection.data_source_config.inputs || [];
    if (existingInputs.length === 0) return;

    try {
      await configureSubsection.mutateAsync({
        subsectionId: selectedSubsectionId,
        data_source_config: {
          inputs: existingInputs,
          dependencies: buildDependenciesForSubmit(),
        },
      });
      toast.success('Dependencies saved');
    } catch (err) {
      console.error('Failed to save dependencies:', err);
      toast.error(getErrorMessage(err, 'Failed to save dependencies'));
    }
  };

  const handleClearDataSource = async () => {
    if (!selectedSubsectionId) return;
    try {
      await configureSubsection.mutateAsync({
        subsectionId: selectedSubsectionId,
        data_source_config: null,
      });
      setSelectedSourceId('');
      setSelectedMethodId('');
      setParameterValues({});
      setDependencySectionIds([]);
      setDependencySubsectionIds([]);
      setParameterErrors({});
      toast.success('Data inputs cleared');
    } catch (err) {
      console.error('Failed to clear data source:', err);
    }
  };

  const handleVersionChange = (versionId: string) => {
    const version = subsection?.versions?.find(v => v.id === versionId);
    if (!version) return;
    if (version.version_number === subsection?.version_number) {
      setSelectedVersionId(null);
    } else {
      setSelectedVersionId(versionId);
    }
  };

  const handleQuickChat = (_context: string, event: React.MouseEvent) => {
    if (!selectedSectionId || !selectedSubsectionId) return;
    const rect = event.currentTarget.getBoundingClientRect();
    openMiniChat(
      selectedSectionId,
      selectedSubsectionId,
      { top: rect.bottom + 8, left: Math.min(rect.left, window.innerWidth - 340) }
    );
  };

  const handleGenerateSubsection = async () => {
    if (!selectedSubsectionId || !subsection) return;

    try {
      setSubsectionGenerating(selectedSubsectionId, true);
      toast.info('Generating content...');
      await generateSubsection.mutateAsync(selectedSubsectionId);
      toast.success('Content generated!');
    } catch (err) {
      console.error('Failed to generate subsection:', err);
      toast.error(getErrorMessage(err, 'Failed to generate content. Please try again.'));
    } finally {
      setSubsectionGenerating(selectedSubsectionId, false);
    }
  };

  const isSubsectionGenerating = selectedSubsectionId
    ? generatingSubsections.has(selectedSubsectionId) || generateSubsection.isPending
    : false;

  // Keyboard shortcuts
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        if (contentDirty) handleSaveContent();
        else if (instructionsDirty) handleSaveInstructions();
        else if (notesDirty) handleSaveNotes();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [
    contentDirty,
    instructionsDirty,
    notesDirty,
    handleSaveContent,
    handleSaveInstructions,
    handleSaveNotes,
  ]);

  // Group data sources by category
  const sourcesByCategory = dataSources?.reduce((acc: Record<string, DataSourceRegistry[]>, ds: DataSourceRegistry) => {
    if (!acc[ds.category]) acc[ds.category] = [];
    acc[ds.category].push(ds);
    return acc;
  }, {} as Record<string, DataSourceRegistry[]>) || {};
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
      && Object.keys(parameterErrors).length === 0
  );

  if (sidebarCollapsed) {
    return (
      <div className="w-10 border-l border-zinc-200 bg-zinc-50 flex flex-col items-center py-4">
        <button
          onClick={toggleSidebar}
          className="p-2 text-zinc-400 hover:text-zinc-600"
          title="Expand sidebar"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
      </div>
    );
  }

  const subsectionLabel = subsection ? positionToLabel(subsection.position) : '';
  const displayTitle = subsection?.title || `Subsection ${subsectionLabel}`;
  const configuredInputs = subsection?.data_source_config?.inputs || [];
  const hasDataSourceConfigured = configuredInputs.length > 0 && configuredInputs.every((input) => {
    if (!input.source_id || !input.method_id) return false;
    if (!dataSources || dataSources.length === 0) return true;

    const inputSource = dataSources.find((source) => source.id === input.source_id);
    if (!inputSource) return false;

    const inputMethod = inputSource.retrieval_methods.find(
      (method) => getMethodId(method) === input.method_id
    );
    if (!inputMethod) return false;

    const inputParameters = input.parameters || {};
    return !(inputMethod.parameters || []).some((parameter) => {
      if (!parameter.required) return false;
      const key = getParameterKey(parameter);
      if (!key) return false;
      const value = (inputParameters as Record<string, unknown>)[key];
      return isMissingValue(value) || hasMissingVariableName(value) || hasMissingPeriodSelector(value);
    });
  });
  const dependencySectionOptions = sections || [];
  const dependencySubsectionOptions = (sections || []).flatMap((section) => (
    section.subsections.map((subsectionItem) => ({
      id: subsectionItem.id,
      sectionTitle: section.title || `Section ${section.position}`,
      subsectionTitle: subsectionItem.title || `Subsection ${positionToLabel(subsectionItem.position)}`,
      subsectionLabel: positionToLabel(subsectionItem.position),
    }))
  ));

  return (
    <div className="w-[420px] border-l border-zinc-200 bg-white flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-zinc-200 flex items-center justify-between bg-zinc-50">
        <h3 className="font-semibold text-zinc-900 text-sm">
          {selectedSubsectionId && subsection
            ? <><span className="text-sky-600 mr-1">{subsectionLabel}.</span>{displayTitle}</>
            : 'Subsection Configuration'}
        </h3>
        <button
          onClick={toggleSidebar}
          className="p-1 text-zinc-400 hover:text-zinc-600"
          title="Collapse sidebar"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {!selectedSubsectionId ? (
          <div className="p-6 text-center text-zinc-500">
            <svg className="w-12 h-12 mx-auto mb-3 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
            </svg>
            <p className="text-sm">Click a subsection to configure it</p>
          </div>
        ) : subsectionLoading ? (
          <div className="p-6 text-center text-zinc-500">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-sky-600 mx-auto mb-2" />
            <p className="text-sm">Loading...</p>
          </div>
        ) : (
          <div className="p-4 space-y-5">
            {/* Instructions Section */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-medium text-zinc-500 uppercase">Instructions</label>
                <div className="flex items-center gap-1">
                  <button
                    onClick={(e) => handleQuickChat('instructions', e)}
                    className="p-1 text-zinc-400 hover:text-sky-600 transition-colors"
                    title="Ask AI about instructions"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                  </button>
                  {instructionsDirty && (
                    <button
                      onClick={handleSaveInstructions}
                      disabled={updateInstructions.isPending}
                      className="px-2 py-0.5 text-xs bg-sky-600 text-white rounded hover:bg-sky-700 disabled:opacity-50"
                    >
                      {updateInstructions.isPending ? '...' : 'Save'}
                    </button>
                  )}
                </div>
              </div>
              <textarea
                value={instructions}
                onChange={(e) => handleInstructionsChange(e.target.value)}
                placeholder="Enter instructions for AI generation..."
                className={`w-full h-24 px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 resize-none ${
                  isViewingHistorical
                    ? 'border-amber-300 bg-amber-50 cursor-not-allowed'
                    : 'border-zinc-300 focus:ring-sky-500'
                }`}
                readOnly={isViewingHistorical}
              />
            </div>

            {/* Content Section */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <label className="text-xs font-medium text-zinc-500 uppercase">Content</label>
                  {contentDirty && (
                    <span className="text-xs text-amber-600">Unsaved</span>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  {/* Version selector */}
                  {subsection?.versions && subsection.versions.length > 0 && (
                    <select
                      className="text-xs border border-zinc-300 rounded px-1.5 py-0.5 focus:outline-none focus:ring-1 focus:ring-sky-500"
                      value={selectedVersionId || subsection.versions.find(v => v.version_number === subsection.version_number)?.id || ''}
                      onChange={(e) => handleVersionChange(e.target.value)}
                    >
                      {subsection.versions.map((v: VersionSummary) => (
                        <option key={v.id} value={v.id}>
                          v{v.version_number}{v.version_number === subsection.version_number ? ' (current)' : ''}
                        </option>
                      ))}
                    </select>
                  )}
                  {!isViewingHistorical && contentDirty && (
                    <button
                      onClick={handleSaveContent}
                      disabled={saveVersion.isPending}
                      className="px-2 py-0.5 text-xs bg-sky-600 text-white rounded hover:bg-sky-700 disabled:opacity-50"
                    >
                      {saveVersion.isPending ? '...' : 'Save'}
                    </button>
                  )}
                </div>
              </div>
              {isViewingHistorical && (
                <div className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded mb-2">
                  Viewing historical version (read-only)
                </div>
              )}
              <textarea
                value={content}
                onChange={(e) => handleContentChange(e.target.value)}
                placeholder="Content will appear here..."
                className={`w-full h-32 px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 resize-y font-mono ${
                  isViewingHistorical
                    ? 'border-amber-300 bg-amber-50 cursor-not-allowed'
                    : 'border-zinc-300 focus:ring-sky-500'
                }`}
                readOnly={isViewingHistorical}
              />
            </div>

            {/* Notes Section */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-medium text-zinc-500 uppercase">Notes</label>
                <div className="flex items-center gap-1">
                  <button
                    onClick={(e) => handleQuickChat('notes', e)}
                    className="p-1 text-zinc-400 hover:text-sky-600 transition-colors"
                    title="Ask AI about notes"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                  </button>
                  {notesDirty && (
                    <button
                      onClick={handleSaveNotes}
                      disabled={updateNotes.isPending}
                      className="px-2 py-0.5 text-xs bg-sky-600 text-white rounded hover:bg-sky-700 disabled:opacity-50"
                    >
                      {updateNotes.isPending ? '...' : 'Save'}
                    </button>
                  )}
                </div>
              </div>
              <textarea
                value={notes}
                onChange={(e) => handleNotesChange(e.target.value)}
                placeholder="Add notes for this subsection..."
                className="w-full h-20 px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 resize-none"
              />
            </div>

            {/* Data Source Section */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-medium text-zinc-500 uppercase">Data Inputs</label>
                <button
                  onClick={(e) => handleQuickChat('data', e)}
                  className="p-1 text-zinc-400 hover:text-sky-600 transition-colors"
                  title="Ask AI about data"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </button>
              </div>

              {/* Current config display */}
              {subsection?.data_source_config && (
                <div className="mb-2 p-2 bg-sky-50 rounded border border-sky-200">
                  <div className="flex items-center justify-between">
                    <div className="text-xs text-sky-700 font-medium">
                      Configured Inputs: {configuredInputs.length}
                    </div>
                    <button
                      onClick={handleClearDataSource}
                      className="text-sky-400 hover:text-sky-600"
                      title="Clear all data inputs"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                  <div className="mt-2 space-y-1">
                    {configuredInputs.map((input, index) => {
                      const inputSource = dataSources?.find((source) => source.id === input.source_id);
                      const inputMethod = inputSource?.retrieval_methods.find(
                        (method) => getMethodId(method) === input.method_id
                      );
                      return (
                        <div
                          key={`${input.source_id}-${input.method_id}-${index}`}
                          className="flex items-center justify-between rounded border border-sky-100 bg-white px-2 py-1"
                        >
                          <div className="text-[11px] text-sky-700">
                            <p>{inputSource?.name || input.source_id}</p>
                            <p className="text-sky-600">{inputMethod?.name || input.method_id}</p>
                          </div>
                          <button
                            onClick={() => handleRemoveDataInput(index)}
                            className="text-sky-400 hover:text-red-600"
                            title="Remove input"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Source selector */}
              <select
                value={selectedSourceId}
                onChange={(e) => handleSourceChange(e.target.value)}
                className="w-full px-2 py-1.5 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500 mb-2"
              >
                <option value="">Select a source...</option>
                {Object.entries(sourcesByCategory).map(([category, sources]) => (
                  <optgroup key={category} label={category}>
                    {sources.map((ds: DataSourceRegistry) => (
                      <option key={ds.id} value={ds.id}>
                        {ds.name}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>

              {/* Method selector */}
              {selectedSourceId && methods.length > 0 && (
                <select
                  value={selectedMethodId}
                  onChange={(e) => handleMethodChange(e.target.value)}
                  className="w-full px-2 py-1.5 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500 mb-2"
                >
                  <option value="">Select a method...</option>
                  {methods.map((method: RetrievalMethod) => (
                    <option key={getMethodId(method)} value={getMethodId(method)}>
                      {method.name}
                    </option>
                  ))}
                </select>
              )}

              {/* Parameter inputs */}
              {selectedMethod && methodParameters.length > 0 && (
                <div className="space-y-2 mb-2">
                  {methodParameters.map((parameter) => {
                    const parameterKey = getParameterKey(parameter);
                    if (!parameterKey) return null;
                    const label = getParameterLabel(parameter, parameterKey);
                    const parameterType = parameter.type.toLowerCase();
                    const value = parameterValues[parameterKey];
                    const options = parameter.options || parameter.enum || [];
                    const arrayItemOptions = parameter.items?.options || parameter.items?.enum || [];
                    const periodOptions = getPeriodSelectorOptions(parameterType);
                    const supportsPeriodMode = periodOptions.length > 0;
                    const isVariableMode = isVariableBindingCandidate(value);
                    const isPeriodMode = isPeriodBindingCandidate(value);
                    const mode: 'literal' | 'variable' | 'period' = isVariableMode ? 'variable' : isPeriodMode ? 'period' : 'literal';
                    const variableBinding = isVariableMode ? toVariableBinding(value) : null;
                    const variableName = variableBinding?.$var || '';
                    const variableDefault = variableBinding?.$default;
                    const periodBinding = isPeriodMode ? toPeriodBinding(value) : null;
                    const periodSelector = periodBinding?.$period || '';
                    const periodCount = periodBinding?.$count;

                    return (
                      <div key={parameterKey}>
                        <div className="flex items-center justify-between mb-1">
                          <label className="block text-xs text-zinc-600">
                            {label}
                            {parameter.required && <span className="text-red-500"> *</span>}
                          </label>
                          <div className="inline-flex rounded border border-zinc-200 overflow-hidden">
                            <button
                              type="button"
                              onClick={() => handleParameterModeChange(parameterKey, parameterType, 'literal')}
                              className={`px-2 py-0.5 text-[11px] ${
                                mode === 'literal' ? 'bg-sky-100 text-sky-700' : 'bg-white text-zinc-600 hover:bg-zinc-50'
                              }`}
                            >
                              Value
                            </button>
                            <button
                              type="button"
                              onClick={() => handleParameterModeChange(parameterKey, parameterType, 'variable')}
                              className={`px-2 py-0.5 text-[11px] border-l border-zinc-200 ${
                                mode === 'variable' ? 'bg-sky-100 text-sky-700' : 'bg-white text-zinc-600 hover:bg-zinc-50'
                              }`}
                            >
                              Variable
                            </button>
                            {supportsPeriodMode && (
                              <button
                                type="button"
                                onClick={() => handleParameterModeChange(parameterKey, parameterType, 'period')}
                                className={`px-2 py-0.5 text-[11px] border-l border-zinc-200 ${
                                  mode === 'period' ? 'bg-sky-100 text-sky-700' : 'bg-white text-zinc-600 hover:bg-zinc-50'
                                }`}
                              >
                                Period
                              </button>
                            )}
                          </div>
                        </div>

                        {mode === 'variable' ? (
                          <div className="space-y-2">
                            <input
                              type="text"
                              value={variableName}
                              onChange={(e) => handleVariableNameChange(parameterKey, e.target.value)}
                              placeholder="Variable name (example: fiscal_quarter)"
                              className="w-full px-2 py-1.5 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500 font-mono"
                            />
                            <div>
                              <label className="block text-[11px] text-zinc-500 mb-1">Default (optional)</label>

                              {parameterType === 'enum' && (
                                <select
                                  value={typeof variableDefault === 'string' ? variableDefault : ''}
                                  onChange={(e) => handleVariableDefaultChange(parameterKey, e.target.value)}
                                  className="w-full px-2 py-1.5 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
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
                                  onChange={(e) => handleVariableDefaultChange(
                                    parameterKey,
                                    e.target.value === '' ? undefined : e.target.value === 'true'
                                  )}
                                  className="w-full px-2 py-1.5 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
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
                                  onChange={(e) => {
                                    const selected = Array.from(e.target.selectedOptions).map((option) => option.value);
                                    handleVariableDefaultChange(parameterKey, selected);
                                  }}
                                  className="w-full px-2 py-1.5 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500 h-24"
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
                                  onChange={(e) => handleVariableDefaultChange(parameterKey, e.target.value)}
                                  placeholder='{"key":"value"}'
                                  className="w-full h-20 px-2 py-1.5 text-xs font-mono border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
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
                                  onChange={(e) => handleVariableDefaultChange(parameterKey, e.target.value)}
                                  placeholder={parameterType === 'array' ? 'Comma-separated values' : 'No default'}
                                  className="w-full px-2 py-1.5 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
                                />
                              )}
                            </div>
                          </div>
                        ) : mode === 'period' ? (
                          <div className="space-y-2">
                            <select
                              value={periodSelector}
                              onChange={(e) => handlePeriodSelectorChange(parameterKey, e.target.value)}
                              className="w-full px-2 py-1.5 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
                            >
                              <option value="">Select period selector...</option>
                              {periodOptions.map((option) => (
                                <option key={option.value} value={option.value}>{option.label}</option>
                              ))}
                            </select>

                            {periodSelector === 'trailing_quarters' && (
                              <div>
                                <label className="block text-[11px] text-zinc-500 mb-1">Number of quarters</label>
                                <input
                                  type="number"
                                  min={1}
                                  value={periodCount === undefined ? 4 : periodCount}
                                  onChange={(e) => handlePeriodCountChange(parameterKey, e.target.value)}
                                  className="w-full px-2 py-1.5 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
                                />
                              </div>
                            )}
                          </div>
                        ) : (
                          <>
                            {parameterType === 'enum' && (
                              <select
                                value={typeof value === 'string' ? value : ''}
                                onChange={(e) => handleParameterChange(parameterKey, e.target.value)}
                                className="w-full px-2 py-1.5 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
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
                                  onChange={(e) => handleParameterChange(parameterKey, e.target.checked)}
                                  className="rounded border-zinc-300 text-sky-600 focus:ring-sky-500"
                                />
                                Enabled
                              </label>
                            )}

                            {parameterType === 'array' && arrayItemOptions.length > 0 && (
                              <select
                                multiple
                                value={Array.isArray(value) ? value.map((item) => String(item)) : []}
                                onChange={(e) => {
                                  const selected = Array.from(e.target.selectedOptions).map((option) => option.value);
                                  handleParameterChange(parameterKey, selected);
                                }}
                                className="w-full px-2 py-1.5 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500 h-24"
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
                                onChange={(e) => handleParameterChange(parameterKey, e.target.value)}
                                placeholder='{"key":"value"}'
                                className="w-full h-20 px-2 py-1.5 text-xs font-mono border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
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
                                onChange={(e) => handleParameterChange(parameterKey, e.target.value)}
                                placeholder={parameterType === 'array' ? 'Comma-separated values' : ''}
                                className="w-full px-2 py-1.5 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
                              />
                            )}
                          </>
                        )}

                        {parameterErrors[parameterKey] && (
                          <p className="text-xs text-red-600 mt-1">{parameterErrors[parameterKey]}</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Dependency selectors */}
              {(dependencySectionOptions.length > 0 || dependencySubsectionOptions.length > 0) && (
                <div className="mb-2 rounded border border-zinc-200 p-2">
                  <p className="text-xs font-medium text-zinc-600 uppercase mb-2">Context Dependencies</p>

                  {dependencySectionOptions.length > 0 && (
                    <div className="mb-2">
                      <p className="text-[11px] text-zinc-500 mb-1">Sections</p>
                      <div className="space-y-1 max-h-28 overflow-y-auto">
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
                      <p className="text-[11px] text-zinc-500 mb-1">Subsections</p>
                      <div className="space-y-1 max-h-32 overflow-y-auto">
                        {dependencySubsectionOptions.map((option) => {
                          const isSelf = option.id === selectedSubsectionId;
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

                  <div className="mt-2">
                    <button
                      onClick={handleSaveDependencies}
                      disabled={configureSubsection.isPending || configuredInputs.length === 0}
                      className="w-full px-2 py-1 text-xs bg-zinc-200 text-zinc-700 rounded hover:bg-zinc-300 disabled:opacity-50"
                    >
                      {configureSubsection.isPending ? 'Saving...' : 'Save Dependencies'}
                    </button>
                  </div>
                </div>
              )}

              {/* Configure button */}
              {selectedSourceId && selectedMethodId && (
                <button
                  onClick={handleConfigureDataSource}
                  disabled={configureSubsection.isPending || !canConfigureDataSource}
                  className="w-full px-3 py-1.5 text-sm bg-sky-600 text-white rounded hover:bg-sky-700 disabled:opacity-50"
                >
                  {configureSubsection.isPending ? 'Saving...' : 'Add Data Input'}
                </button>
              )}

              {selectedSourceId && selectedMethodId && missingRequiredParameterKeys.length > 0 && (
                <p className="text-xs text-amber-600 mt-2">
                  Fill all required parameters before configuring.
                </p>
              )}

              {selectedSource && (
                <p className="text-xs text-zinc-500 mt-2">{selectedSource.description}</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Generate button at bottom */}
      {selectedSubsectionId && subsection && (
        <div className="p-4 border-t border-zinc-200 bg-zinc-50">
          <button
            onClick={handleGenerateSubsection}
            disabled={isSubsectionGenerating || !hasDataSourceConfigured}
            className="w-full px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            title={
              hasDataSourceConfigured
                ? 'Generate content for this subsection'
                : 'Configure source, method, and required parameters before generating'
            }
          >
            {isSubsectionGenerating ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                Generating...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Generate This Subsection
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
