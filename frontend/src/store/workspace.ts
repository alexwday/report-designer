import { create } from 'zustand';

interface MiniChatState {
  isOpen: boolean;
  sectionId: string | null;
  subsectionId: string | null;
  position: { top: number; left: number } | null;
}

interface SubsectionInfo {
  label: string;  // A, B, C
  title: string | null;
}

interface WorkspaceState {
  // Selections
  selectedSectionId: string | null;
  selectedSubsectionId: string | null;
  selectedSubsectionInfo: SubsectionInfo | null;

  // Generation tracking
  generatingSubsections: Set<string>;
  generatingSections: Set<string>;
  isGeneratingReport: boolean;

  // UI State
  chatExpanded: boolean;
  sidebarCollapsed: boolean;
  miniChat: MiniChatState;

  // Actions
  setSelectedSection: (id: string | null) => void;
  setSelectedSubsection: (id: string | null, subsectionInfo?: SubsectionInfo | null) => void;
  setSubsectionGenerating: (subsectionId: string, generating: boolean) => void;
  setSectionGenerating: (sectionId: string, generating: boolean) => void;
  setReportGenerating: (generating: boolean) => void;
  toggleChat: () => void;
  toggleSidebar: () => void;
  openMiniChat: (sectionId: string, subsectionId: string, position?: { top: number; left: number }) => void;
  closeMiniChat: () => void;
  reset: () => void;
}

const initialMiniChat: MiniChatState = {
  isOpen: false,
  sectionId: null,
  subsectionId: null,
  position: null,
};

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  // Initial state
  selectedSectionId: null,
  selectedSubsectionId: null,
  selectedSubsectionInfo: null,
  generatingSubsections: new Set(),
  generatingSections: new Set(),
  isGeneratingReport: false,
  chatExpanded: true,
  sidebarCollapsed: false,
  miniChat: initialMiniChat,

  // Actions
  setSelectedSection: (id) =>
    set({ selectedSectionId: id, selectedSubsectionId: null, selectedSubsectionInfo: null }),

  setSelectedSubsection: (id, subsectionInfo) =>
    set({ selectedSubsectionId: id, selectedSubsectionInfo: subsectionInfo || null }),

  setSubsectionGenerating: (subsectionId, generating) =>
    set((state) => {
      const newSet = new Set(state.generatingSubsections);
      if (generating) {
        newSet.add(subsectionId);
      } else {
        newSet.delete(subsectionId);
      }
      return { generatingSubsections: newSet };
    }),

  setSectionGenerating: (sectionId, generating) =>
    set((state) => {
      const newSet = new Set(state.generatingSections);
      if (generating) {
        newSet.add(sectionId);
      } else {
        newSet.delete(sectionId);
      }
      return { generatingSections: newSet };
    }),

  setReportGenerating: (generating) =>
    set({ isGeneratingReport: generating }),

  toggleChat: () =>
    set((state) => ({ chatExpanded: !state.chatExpanded })),

  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  openMiniChat: (sectionId, subsectionId, position) =>
    set({
      miniChat: {
        isOpen: true,
        sectionId,
        subsectionId,
        position: position || null,
      },
    }),

  closeMiniChat: () =>
    set({ miniChat: initialMiniChat }),

  reset: () =>
    set({
      selectedSectionId: null,
      selectedSubsectionId: null,
      selectedSubsectionInfo: null,
      generatingSubsections: new Set(),
      generatingSections: new Set(),
      isGeneratingReport: false,
      chatExpanded: true,
      sidebarCollapsed: false,
      miniChat: initialMiniChat,
    }),
}));
