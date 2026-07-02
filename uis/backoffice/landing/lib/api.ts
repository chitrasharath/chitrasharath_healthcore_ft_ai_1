const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const PUBLIC_AUTH_ROUTES = ["/", "/login", "/register", "/forgot-password", "/reset-password"];

export const NETWORK_ERROR_MESSAGE =
  "Unable to connect. Please check your connection and try again.";

const isNetworkFailure = (error: unknown): boolean =>
  error instanceof TypeError && error.message.toLowerCase().includes("fetch");

const shouldRedirectOnUnauthorized = (): boolean => {
  if (typeof window === "undefined") return false;
  return !PUBLIC_AUTH_ROUTES.includes(window.location.pathname);
};

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem("token");
  const headers = new Headers(options.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  headers.set("Content-Type", "application/json");

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch (error) {
    if (isNetworkFailure(error)) {
      throw new Error(NETWORK_ERROR_MESSAGE);
    }
    throw error;
  }

  if (response.status === 401) {
    localStorage.removeItem("token");
    if (shouldRedirectOnUnauthorized()) {
      window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }

  return response;
}

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type UserProfile = {
  id: number;
  email: string;
  name: string;
  is_active: boolean;
  created_at: string;
};

export const getStoredToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
};

export async function fetchCurrentUser(): Promise<UserProfile | null> {
  const token = getStoredToken();
  if (!token) return null;

  let response: Response;
  try {
    response = await fetch(`${API_URL}/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });
  } catch (error) {
    if (isNetworkFailure(error)) {
      return null;
    }
    throw error;
  }

  if (response.status === 401) {
    localStorage.removeItem("token");
    return null;
  }

  if (!response.ok) {
    throw new Error("Failed to fetch user profile");
  }

  return response.json() as Promise<UserProfile>;
}

export type CredentialVerifyResult = "ok" | "invalid" | "network" | "server_error";

export async function verifyCredentials(
  email: string,
  password: string,
): Promise<CredentialVerifyResult> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch (error) {
    if (isNetworkFailure(error)) {
      return "network";
    }
    throw error;
  }

  if (response.status === 401) return "invalid";
  if (!response.ok) return "server_error";
  return "ok";
}
