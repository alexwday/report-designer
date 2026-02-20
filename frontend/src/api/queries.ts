import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from './client';
import type {
  TemplateSummary,
  Template,
  CreateTemplateRequest,
  UpdateTemplateRequest,
  Section,
  CreateSectionRequest,
  UpdateSectionRequest,
  SectionDeleteResponse,
  Subsection,
  Version,
  SaveVersionRequest,
  SaveVersionResponse,
  UpdateNotesRequest,
  UpdateNotesResponse,
  UpdateInstructionsRequest,
  UpdateInstructionsResponse,
  ConfigureSubsectionRequest,
  ConfigureSubsectionResponse,
  CreateSubsectionRequest,
  CreateSubsectionResponse,
  UpdateTitleRequest,
  UpdateTitleResponse,
  ReorderSubsectionRequest,
  SubsectionDeleteResponse,
  DataSourceRegistry,
  ChatRequest,
  ChatResponse,
  ConversationHistoryResponse,
  PreviewData,
  StartGenerationResponse,
  StartGenerationRequest,
  GenerationJobStatus,
  GenerationRequirementsResponse,
  GenerateSubsectionResponse,
  GenerateSectionResponse,
  Upload,
  TemplateVersionSummary,
  TemplateVersionFull,
  CreateTemplateVersionRequest,
  RestoreVersionResponse,
  ForkTemplateRequest,
  ForkTemplateResponse,
  SetSharedResponse,
} from './types';

// ============ Templates ============

export function useTemplates() {
  return useQuery({
    queryKey: ['templates'],
    queryFn: async () => {
      const { data } = await api.get<TemplateSummary[]>('/templates');
      return data;
    },
  });
}

export function useTemplate(id: string) {
  return useQuery({
    queryKey: ['templates', id],
    queryFn: async () => {
      const { data } = await api.get<{ template: Template; sections_summary: unknown }>(`/templates/${id}`);
      return data.template;
    },
    enabled: !!id,
  });
}

export function useCreateTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: CreateTemplateRequest) => {
      const { data } = await api.post<Template>('/templates', request);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
    },
  });
}

export function useUpdateTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...request }: UpdateTemplateRequest & { id: string }) => {
      const { data } = await api.patch<Template>(`/templates/${id}`, request);
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      queryClient.invalidateQueries({ queryKey: ['templates', data.id] });
    },
  });
}

export function useDeleteTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/templates/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
    },
  });
}

// ============ Sections ============

export function useSections(templateId: string, includeContent = false) {
  return useQuery({
    queryKey: ['sections', templateId, includeContent],
    queryFn: async () => {
      const { data } = await api.get<Section[]>(`/templates/${templateId}/sections`, {
        params: { include_content: includeContent },
      });
      return data;
    },
    enabled: !!templateId,
  });
}

export function useCreateSection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ templateId, ...request }: CreateSectionRequest & { templateId: string }) => {
      const { data } = await api.post<Section>(`/templates/${templateId}/sections`, request);
      return { ...data, templateId };
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['sections', data.templateId] });
      queryClient.invalidateQueries({ queryKey: ['preview', data.templateId] });
      queryClient.invalidateQueries({ queryKey: ['templates', data.templateId] });
    },
  });
}

export function useUpdateSection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, templateId, ...request }: UpdateSectionRequest & { id: string; templateId: string }) => {
      const { data } = await api.patch<Section>(`/sections/${id}`, request);
      return { ...data, templateId };
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['sections', data.templateId] });
      queryClient.invalidateQueries({ queryKey: ['preview', data.templateId] });
    },
  });
}

export function useDeleteSection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, templateId }: { id: string; templateId: string }) => {
      const { data } = await api.delete<SectionDeleteResponse>(`/sections/${id}`);
      return { ...data, templateId };
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['sections', variables.templateId] });
      queryClient.invalidateQueries({ queryKey: ['preview', variables.templateId] });
      queryClient.invalidateQueries({ queryKey: ['templates', variables.templateId] });
    },
  });
}

// ============ Subsections ============

export function useSubsection(subsectionId: string, includeVersions = true) {
  return useQuery({
    queryKey: ['subsection', subsectionId, includeVersions],
    queryFn: async () => {
      const { data } = await api.get<Subsection>(`/subsections/${subsectionId}`, {
        params: { include_versions: includeVersions, version_limit: 10 },
      });
      return data;
    },
    enabled: !!subsectionId,
  });
}

export function useCreateSubsection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ sectionId, templateId, ...request }: CreateSubsectionRequest & { sectionId: string; templateId: string }) => {
      const { data } = await api.post<CreateSubsectionResponse>(`/subsections/sections/${sectionId}/subsections`, request);
      return { ...data, templateId };
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['sections', data.templateId] });
      queryClient.invalidateQueries({ queryKey: ['preview', data.templateId] });
    },
  });
}

export function useUpdateSubsectionTitle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ subsectionId, templateId, ...request }: UpdateTitleRequest & { subsectionId: string; templateId: string }) => {
      const { data } = await api.patch<UpdateTitleResponse>(`/subsections/${subsectionId}/title`, request);
      return { ...data, subsectionId, templateId };
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['subsection', data.subsectionId] });
      queryClient.invalidateQueries({ queryKey: ['sections', data.templateId] });
      queryClient.invalidateQueries({ queryKey: ['preview', data.templateId] });
    },
  });
}

export function useReorderSubsection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ subsectionId, templateId, ...request }: ReorderSubsectionRequest & { subsectionId: string; templateId: string }) => {
      const { data } = await api.patch<Subsection>(`/subsections/${subsectionId}/reorder`, request);
      return { ...data, templateId };
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['subsection', data.id] });
      queryClient.invalidateQueries({ queryKey: ['sections', data.templateId] });
      queryClient.invalidateQueries({ queryKey: ['preview', data.templateId] });
    },
  });
}

export function useDeleteSubsection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ subsectionId, templateId }: { subsectionId: string; templateId: string }) => {
      const { data } = await api.delete<SubsectionDeleteResponse>(`/subsections/${subsectionId}`);
      return { ...data, templateId };
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['sections', variables.templateId] });
      queryClient.invalidateQueries({ queryKey: ['preview', variables.templateId] });
    },
  });
}

export function useUpdateNotes() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ subsectionId, ...request }: UpdateNotesRequest & { subsectionId: string }) => {
      const { data } = await api.patch<UpdateNotesResponse>(`/subsections/${subsectionId}/notes`, request);
      return { ...data, subsectionId };
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['subsection', variables.subsectionId] });
      queryClient.invalidateQueries({ queryKey: ['sections'] });
      queryClient.invalidateQueries({ queryKey: ['preview'] });
    },
  });
}

export function useUpdateInstructions() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ subsectionId, ...request }: UpdateInstructionsRequest & { subsectionId: string }) => {
      const { data } = await api.patch<UpdateInstructionsResponse>(`/subsections/${subsectionId}/instructions`, request);
      return { ...data, subsectionId };
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['subsection', variables.subsectionId] });
      queryClient.invalidateQueries({ queryKey: ['sections'] });
      queryClient.invalidateQueries({ queryKey: ['preview'] });
    },
  });
}

export function useConfigureSubsection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ subsectionId, ...request }: ConfigureSubsectionRequest & { subsectionId: string }) => {
      const { data } = await api.patch<ConfigureSubsectionResponse>(`/subsections/${subsectionId}/config`, request);
      return { ...data, subsectionId };
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['subsection', variables.subsectionId] });
      queryClient.invalidateQueries({ queryKey: ['sections'] });
      queryClient.invalidateQueries({ queryKey: ['preview'] });
    },
  });
}

export function useSaveVersion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ subsectionId, templateId, ...request }: SaveVersionRequest & { subsectionId: string; templateId?: string }) => {
      const { data } = await api.post<SaveVersionResponse>(`/subsections/${subsectionId}/versions`, request);
      return { ...data, subsectionId, templateId };
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['subsection', data.subsectionId] });
      if (data.templateId) {
        queryClient.invalidateQueries({ queryKey: ['sections', data.templateId] });
        queryClient.invalidateQueries({ queryKey: ['preview', data.templateId] });
      }
    },
  });
}

export function useGenerateSubsection(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (subsectionId: string) => {
      const { data } = await api.post<GenerateSubsectionResponse>(`/subsections/${subsectionId}/generate`);
      return data;
    },
    onSuccess: (_, subsectionId) => {
      queryClient.invalidateQueries({ queryKey: ['subsection', subsectionId] });
      queryClient.invalidateQueries({ queryKey: ['sections', templateId] });
      queryClient.invalidateQueries({ queryKey: ['preview', templateId] });
    },
  });
}

export function useGenerateSection(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (sectionId: string) => {
      const { data } = await api.post<GenerateSectionResponse>(`/sections/${sectionId}/generate`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sections', templateId] });
      queryClient.invalidateQueries({ queryKey: ['subsection'] });
      queryClient.invalidateQueries({ queryKey: ['preview', templateId] });
    },
  });
}

// ============ Data Sources ============

export function useDataSourceRegistry(category?: string) {
  return useQuery({
    queryKey: ['dataSourceRegistry', category],
    queryFn: async () => {
      const { data } = await api.get<DataSourceRegistry[]>('/data-sources', {
        params: { category, active_only: true },
      });
      return data;
    },
  });
}

// ============ Versions ============

export function useVersion(versionId: string) {
  return useQuery({
    queryKey: ['version', versionId],
    queryFn: async () => {
      const { data } = await api.get<Version>(`/subsections/versions/${versionId}`);
      return data;
    },
    enabled: !!versionId,
  });
}

// ============ Chat ============

export function useChatMutation(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: ChatRequest) => {
      const { data } = await api.post<ChatResponse>(`/templates/${templateId}/chat`, request);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chatHistory', templateId] });
      // Invalidate sections in case agent created/modified them
      queryClient.invalidateQueries({ queryKey: ['sections', templateId] });
      // Invalidate subsections in case agent updated notes/instructions/content
      queryClient.invalidateQueries({ queryKey: ['subsection'] });
      // Invalidate preview in case content changed
      queryClient.invalidateQueries({ queryKey: ['preview', templateId] });
    },
  });
}

export function useChatHistory(templateId: string) {
  return useQuery({
    queryKey: ['chatHistory', templateId],
    queryFn: async () => {
      const { data } = await api.get<ConversationHistoryResponse>(`/templates/${templateId}/chat/history`);
      return data;
    },
    enabled: !!templateId,
  });
}

// ============ Preview & Export ============

export function usePreview(templateId: string, enabled = true) {
  return useQuery({
    queryKey: ['preview', templateId],
    queryFn: async () => {
      const { data } = await api.get<PreviewData>(`/templates/${templateId}/preview`);
      return data;
    },
    enabled: !!templateId && enabled,
  });
}

export function useExportPdf(templateId: string) {
  return useMutation({
    mutationFn: async () => {
      const response = await api.post(`/templates/${templateId}/export/pdf`, {}, {
        responseType: 'blob',
      });
      return response.data as Blob;
    },
  });
}

// ============ Generation ============

export function useStartGeneration(templateId: string) {
  return useMutation({
    mutationFn: async (request?: StartGenerationRequest) => {
      const { data } = await api.post<StartGenerationResponse>(`/templates/${templateId}/generate`, request || {});
      return data;
    },
  });
}

export function useGenerationRequirements(templateId: string) {
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.get<GenerationRequirementsResponse>(`/templates/${templateId}/generate/requirements`);
      return data;
    },
  });
}

export function useGenerationStatus(templateId: string, jobId: string | null, enabled = true) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: ['generationStatus', templateId, jobId],
    queryFn: async () => {
      const { data } = await api.get<GenerationJobStatus>(`/templates/${templateId}/generate/status/${jobId}`);
      return data;
    },
    enabled: !!templateId && !!jobId && enabled,
    refetchInterval: (query) => {
      // Poll every 2 seconds while in progress
      const status = query.state.data?.status;
      if (status === 'in_progress' || status === 'pending') {
        return 2000;
      }
      // Stop polling when done
      if (status === 'completed') {
        // Invalidate sections to refresh content
        queryClient.invalidateQueries({ queryKey: ['sections', templateId] });
      }
      return false;
    },
  });
}

// ============ Uploads ============

export function useUploads(templateId: string) {
  return useQuery({
    queryKey: ['uploads', templateId],
    queryFn: async () => {
      const { data } = await api.get<Upload[]>(`/templates/${templateId}/uploads`);
      return data;
    },
    enabled: !!templateId,
  });
}

export function useUploadFile(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      const { data } = await api.post<Upload>(`/templates/${templateId}/uploads`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['uploads', templateId] });
    },
  });
}

export function useDeleteUpload(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (uploadId: string) => {
      const { data } = await api.delete(`/templates/${templateId}/uploads/${uploadId}`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['uploads', templateId] });
    },
  });
}

// ============ Template Versions ============

export function useTemplateVersions(templateId: string) {
  return useQuery({
    queryKey: ['templateVersions', templateId],
    queryFn: async () => {
      const { data } = await api.get<TemplateVersionSummary[]>(`/templates/${templateId}/versions`);
      return data;
    },
    enabled: !!templateId,
  });
}

export function useTemplateVersion(templateId: string, versionId: string) {
  return useQuery({
    queryKey: ['templateVersion', templateId, versionId],
    queryFn: async () => {
      const { data } = await api.get<TemplateVersionFull>(`/templates/${templateId}/versions/${versionId}`);
      return data;
    },
    enabled: !!templateId && !!versionId,
  });
}

export function useCreateTemplateVersion(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: CreateTemplateVersionRequest) => {
      const { data } = await api.post<TemplateVersionSummary>(`/templates/${templateId}/versions`, request);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templateVersions', templateId] });
    },
  });
}

export function useRestoreTemplateVersion(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (versionId: string) => {
      const { data } = await api.post<RestoreVersionResponse>(
        `/templates/${templateId}/versions/${versionId}/restore`
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates', templateId] });
      queryClient.invalidateQueries({ queryKey: ['sections', templateId] });
      queryClient.invalidateQueries({ queryKey: ['templateVersions', templateId] });
    },
  });
}

export function useForkTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ templateId, ...request }: ForkTemplateRequest & { templateId: string }) => {
      const { data } = await api.post<ForkTemplateResponse>(`/templates/${templateId}/fork`, request);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
    },
  });
}

export function useSharedTemplates() {
  return useQuery({
    queryKey: ['sharedTemplates'],
    queryFn: async () => {
      const { data } = await api.get<TemplateSummary[]>('/templates/shared');
      return data;
    },
  });
}

export function useSetTemplateShared(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (isShared: boolean) => {
      const { data } = await api.patch<SetSharedResponse>(`/templates/${templateId}/share`, {
        is_shared: isShared,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates', templateId] });
      queryClient.invalidateQueries({ queryKey: ['sharedTemplates'] });
    },
  });
}
