import { create } from "zustand";

import { authApi } from "@/api/auth";
import { ApiClientError } from "@/api/client";
import type { LoginCredentials, RegisterCredentials, User } from "@/types/auth";

interface AuthState {
  user: User | null;
  // In-memory only, by design — never persisted to localStorage/cookies.
  // The refresh token (the credential that actually matters long-term)
  // lives solely in the httpOnly cookie the browser manages; on reload,
  // restoreSession() re-derives a fresh access token from that cookie.
  accessToken: string | null;
  isLoading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  logout: () => Promise<void>;
  restoreSession: () => Promise<void>;
  clearError: () => void;
}

function setSession(set: (partial: Partial<AuthState>) => void, user: User, accessToken: string) {
  set({
    user,
    accessToken,
    isAuthenticated: true,
    error: null,
  });
}

export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  accessToken: null,
  isLoading: false,
  error: null,
  isAuthenticated: false,

  clearError: () => set({ error: null }),

  login: async (credentials) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authApi.login(credentials);
      setSession(set, response.user, response.access_token);
    } catch (error) {
      const message = error instanceof ApiClientError ? error.message : "Login failed";
      set({ error: message, isAuthenticated: false });
      throw error;
    } finally {
      set({ isLoading: false });
    }
  },

  register: async (credentials) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authApi.register(credentials);
      setSession(set, response.user, response.access_token);
    } catch (error) {
      const message = error instanceof ApiClientError ? error.message : "Registration failed";
      set({ error: message, isAuthenticated: false });
      throw error;
    } finally {
      set({ isLoading: false });
    }
  },

  logout: async () => {
    try {
      await authApi.logout();
    } catch {
      // Best-effort logout — still clear local state below regardless.
    }
    set({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      error: null,
    });
  },

  restoreSession: async () => {
    // No refresh token in JS-reachable state to check — just ask the
    // server: it either has a valid httpOnly refresh cookie or it doesn't.
    set({ isLoading: true });
    try {
      const response = await authApi.refresh();
      setSession(set, response.user, response.access_token);
    } catch {
      set({ user: null, accessToken: null, isAuthenticated: false });
    } finally {
      set({ isLoading: false });
    }
  },
}));
