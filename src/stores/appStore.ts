import { create } from "zustand";

interface AppState {
  activeScanId: string | null;
  activeBugId: string | null;
  selectedProjectId: string | null;
  setActiveScanId: (id: string | null) => void;
  setActiveBugId: (id: string | null) => void;
  setSelectedProjectId: (id: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  activeScanId: null,
  activeBugId: null,
  selectedProjectId: null,
  setActiveScanId: (id) => set({ activeScanId: id }),
  setActiveBugId: (id) => set({ activeBugId: id }),
  setSelectedProjectId: (id) => set({ selectedProjectId: id }),
}));
