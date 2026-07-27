import { apiRequest, readCsrfCookie } from "@/api/client";
import type {
  AuthResponse,
  LoginCredentials,
  RegisterCredentials,
  User,
} from "@/types/auth";

function csrfHeaders(): Record<string, string> {
  const token = readCsrfCookie();
  return token ? { "X-CSRF-Token": token } : {};
}

export const authApi = {
  register(credentials: RegisterCredentials) {
    return apiRequest<AuthResponse>("/auth/register", {
      method: "POST",
      body: credentials,
    });
  },

  login(credentials: LoginCredentials) {
    return apiRequest<AuthResponse>("/auth/login", {
      method: "POST",
      body: credentials,
    });
  },

  // Refresh token travels only as an httpOnly cookie — nothing to pass here.
  refresh() {
    return apiRequest<AuthResponse>("/auth/refresh", {
      method: "POST",
      headers: csrfHeaders(),
    });
  },

  logout() {
    return apiRequest<{ message: string }>("/auth/logout", {
      method: "POST",
      headers: csrfHeaders(),
    });
  },

  me(accessToken: string) {
    return apiRequest<User>("/auth/me", {
      method: "GET",
      token: accessToken,
    });
  },

  changePassword(currentPassword: string, newPassword: string, accessToken: string) {
    return apiRequest<{ message: string }>("/auth/change-password", {
      method: "POST",
      body: { current_password: currentPassword, new_password: newPassword },
      token: accessToken,
    });
  },

  forgotPassword(email: string) {
    return apiRequest<{ message: string }>("/auth/forgot-password", {
      method: "POST",
      body: { email },
    });
  },

  resetPassword(token: string, newPassword: string) {
    return apiRequest<{ message: string }>("/auth/reset-password", {
      method: "POST",
      body: { token, new_password: newPassword },
    });
  },

  verifyEmail(token: string) {
    return apiRequest<{ message: string }>("/auth/verify-email", {
      method: "POST",
      body: { token },
    });
  },

  resendVerification(accessToken: string) {
    return apiRequest<{ message: string }>("/auth/resend-verification", {
      method: "POST",
      token: accessToken,
    });
  },
};
