import { createSupabaseBrowserClient } from "./supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_URL) {
  throw new Error("NEXT_PUBLIC_API_URL is not configured");
}

/** Typed wrapper around fetch for FastAPI backend calls. Attaches the Supabase access token as a Bearer header. */
async function apiFetch<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const supabase = createSupabaseBrowserClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };

  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    const message = await response.text().catch(() => response.statusText);
    throw new Error(`API error ${response.status}: ${message}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  get<T>(path: string): Promise<T> {
    return apiFetch<T>(path, { method: "GET" });
  },
  post<T>(path: string, body: unknown): Promise<T> {
    return apiFetch<T>(path, { method: "POST", body: JSON.stringify(body) });
  },
  put<T>(path: string, body: unknown): Promise<T> {
    return apiFetch<T>(path, { method: "PUT", body: JSON.stringify(body) });
  },
  delete<T>(path: string): Promise<T> {
    return apiFetch<T>(path, { method: "DELETE" });
  },
};
