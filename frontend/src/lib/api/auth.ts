/**
 * Authentication API Client Layer for GODDESS AI 2.0.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export interface UserSchema {
  id: number;
  username: string;
  email?: string;
  role: "OWNER" | "ADMIN" | "OPERATOR" | "VIEWER";
  is_active: boolean;
  permissions: string[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserSchema;
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("goddess_auth_token") || sessionStorage.getItem("goddess_auth_token");
}

export function setStoredToken(token: string, remember: boolean = true) {
  if (typeof window === "undefined") return;
  if (remember) {
    localStorage.setItem("goddess_auth_token", token);
  } else {
    sessionStorage.setItem("goddess_auth_token", token);
  }
}

export function clearStoredToken() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("goddess_auth_token");
  sessionStorage.removeItem("goddess_auth_token");
}

export function getAuthHeaders(): HeadersInit {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Authentication failed with status ${res.status}`);
  }

  const data: LoginResponse = await res.json();
  setStoredToken(data.access_token);
  return data;
}

export async function fetchCurrentUser(): Promise<UserSchema> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: getAuthHeaders(),
  });

  if (!res.ok) {
    clearStoredToken();
    throw new Error(`Failed to fetch current user session`);
  }

  return res.json();
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
  } finally {
    clearStoredToken();
  }
}
