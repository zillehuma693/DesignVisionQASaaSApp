import { env } from "@/config/env";
import { useAuthStore } from "@/stores/authStore";
import { authApi } from "@/api/auth";
import type { ApiError } from "@/types/auth";

export class ApiClientError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  token?: string | null;
};

function parseErrorMessage(payload: ApiError, status: number): string {
  if (typeof payload.detail === "string") {
    return payload.detail;
  }
  if (Array.isArray(payload.detail) && payload.detail.length > 0) {
    return payload.detail.map((item) => item.msg).join(", ");
  }
  return `Request failed with status ${status}`;
}

/** Reads the non-httpOnly CSRF cookie set alongside the httpOnly refresh
 * cookie, so it can be echoed back as a header (double-submit pattern). */
export function readCsrfCookie(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

let refreshPromise: Promise<string | null> | null = null;

function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await authApi.refresh();
        useAuthStore.setState({
          user: res.user,
          accessToken: res.access_token,
          isAuthenticated: true,
        });
        return res.access_token;
      } catch {
        useAuthStore.setState({
          user: null,
          accessToken: null,
          isAuthenticated: false,
        });
        return null;
      }
    })().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}, _isRetry = false): Promise<T> {
  const { body, token, headers, ...rest } = options;

  const response = await fetch(`${env.apiBaseUrl}${path}`, {
    ...rest,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401 && token && !_isRetry && !path.startsWith("/auth/")) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      return apiRequest<T>(path, { ...options, token: newToken }, true);
    }
  }

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as ApiError;
      message = parseErrorMessage(payload, response.status);
    } catch {
      // ignore JSON parse errors
    }
    throw new ApiClientError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
