import { apiRequest } from "@/api/client";
import { useAuthStore } from "@/stores/authStore";
import type { AuthProfile, AuthSession, DashboardData, Project, Scan, ScanDetail, TeamMember, UserSettings, Bug } from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

function token() {
  return useAuthStore.getState().accessToken;
}

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: () => apiRequest<DashboardData>("/dashboard", { token: token() }),
    enabled: !!token(),
  });
}

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: async () => {
      const res = await apiRequest<{ items: Project[] }>("/projects", { token: token() });
      return res.items;
    },
    enabled: !!token(),
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; base_url: string }) =>
      apiRequest<Project>("/projects", { method: "POST", body: data, token: token() }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiRequest<void>(`/projects/${id}`, { method: "DELETE", token: token() }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
}

export function useScans(projectId?: string | null) {
  const qs = projectId ? `?project_id=${projectId}` : "";
  return useQuery({
    queryKey: ["scans", projectId],
    queryFn: async () => {
      const res = await apiRequest<{ items: Scan[] }>(`/scans${qs}`, { token: token() });
      return res.items;
    },
    enabled: !!token(),
  });
}

export function useScan(scanId: string | null, poll = false) {
  return useQuery({
    queryKey: ["scan", scanId],
    queryFn: () => apiRequest<ScanDetail>(`/scans/${scanId}`, { token: token() }),
    enabled: !!token() && !!scanId,
    refetchInterval: poll ? 1500 : false,
  });
}

export function useCreateScan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      url: string; project_id?: string; branch?: string; browser?: string; viewport?: string;
      auth_profile_id?: string; fill_forms?: boolean;
    }) => apiRequest<Scan>("/scans", { method: "POST", body: data, token: token() }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scans"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useStartAuthSession() {
  return useMutation({
    mutationFn: (url: string) =>
      apiRequest<AuthSession>("/auth-sessions", { method: "POST", body: { url }, token: token() }),
  });
}

export function useAuthSessionStatus(sessionId: string | null, poll: boolean) {
  return useQuery({
    queryKey: ["auth-session", sessionId],
    queryFn: () => apiRequest<AuthSession>(`/auth-sessions/${sessionId}`, { token: token() }),
    enabled: !!token() && !!sessionId && poll,
    refetchInterval: poll ? 1500 : false,
    retry: false,
    // After Save/Cancel the session is deleted; in-flight polls 404 — that's expected.
    throwOnError: false,
  });
}

export function useCompleteAuthSession() {
  return useMutation({
    mutationFn: (sessionId: string) =>
      apiRequest<AuthProfile>(`/auth-sessions/${sessionId}/complete`, { method: "POST", token: token() }),
  });
}

export function useCancelAuthSession() {
  return useMutation({
    mutationFn: (sessionId: string) =>
      apiRequest<void>(`/auth-sessions/${sessionId}`, { method: "DELETE", token: token() }),
  });
}

export function useBug(bugId: string | null) {
  return useQuery({
    queryKey: ["bug", bugId],
    queryFn: () => apiRequest<Bug>(`/bugs/${bugId}`, { token: token() }),
    enabled: !!token() && !!bugId,
  });
}

export function useTeam() {
  return useQuery({
    queryKey: ["team"],
    queryFn: async () => {
      const res = await apiRequest<{ items: TeamMember[]; total: number; active: number; invited: number }>("/team", { token: token() });
      return res;
    },
    enabled: !!token(),
  });
}

export function useInviteMember() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; email: string; role: string }) =>
      apiRequest<TeamMember>("/team", { method: "POST", body: data, token: token() }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["team"] }),
  });
}

export function useSettings() {
  return useQuery({
    queryKey: ["settings"],
    queryFn: () => apiRequest<UserSettings>("/settings", { token: token() }),
    enabled: !!token(),
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<UserSettings>) =>
      apiRequest<UserSettings>("/settings", { method: "PATCH", body: data, token: token() }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  });
}

export function getExportUrl(scanId: string) {
  return `${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1"}/scans/${scanId}/export`;
}
