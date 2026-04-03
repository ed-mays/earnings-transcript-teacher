import { createSupabaseBrowserClient } from "./supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_URL) {
  throw new Error("NEXT_PUBLIC_API_URL is not configured");
}

interface StreamDefineCallbacks {
  onToken: (token: string) => void;
  onDone: () => void;
  onError: (message: string) => void;
}

/** Stream an on-demand LLM definition for a term not in the static glossary. */
export async function streamDefine(
  ticker: string,
  term: string,
  callbacks: StreamDefineCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const supabase = createSupabaseBrowserClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const response = await fetch(`${API_URL}/api/calls/${ticker}/define`, {
    method: "POST",
    headers,
    body: JSON.stringify({ term }),
    signal,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText);
    callbacks.onError(`API error ${response.status}: ${text}`);
    return;
  }

  if (!response.body) {
    callbacks.onError("Response body is empty");
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let terminated = false;

  signal?.addEventListener("abort", () => { reader.cancel().catch(() => {}); });

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (signal?.aborted) break;

      buffer += decoder.decode(value, { stream: true });

      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";

      for (const event of events) {
        const dataLine = event.split("\n").find((line) => line.startsWith("data: "));
        if (!dataLine) continue;

        const jsonStr = dataLine.slice("data: ".length);
        let parsed: { type: string; content?: string; message?: string };
        try {
          parsed = JSON.parse(jsonStr);
        } catch {
          continue;
        }

        if (parsed.type === "token" && parsed.content !== undefined) {
          callbacks.onToken(parsed.content);
        } else if (parsed.type === "done") {
          terminated = true;
          callbacks.onDone();
        } else if (parsed.type === "error") {
          terminated = true;
          callbacks.onError(parsed.message ?? "Unknown error");
        }
      }
    }
  } catch (err: unknown) {
    if (!signal?.aborted) {
      terminated = true;
      callbacks.onError(err instanceof Error ? err.message : "Stream read error");
    }
  } finally {
    if (!terminated && !signal?.aborted) {
      callbacks.onError("Stream closed without response");
    }
  }
}
