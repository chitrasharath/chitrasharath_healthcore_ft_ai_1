const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const PUBLIC_AUTH_ROUTES = ["/login", "/register", "/forgot-password", "/reset-password"];

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

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

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
