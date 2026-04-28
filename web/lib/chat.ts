import { createSupabaseBrowserClient } from "./supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_URL) {
  throw new Error("NEXT_PUBLIC_API_URL is not configured");
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface StreamChatCallbacks {
  onToken: (token: string) => void;
  onDone: (sessionId: string) => void;
  onError: (message: string) => void;
}

/** Stream a Feynman chat response via SSE. Uses fetch + ReadableStream because EventSource cannot POST.
 *  Pass an AbortSignal to cancel the in-flight stream when the caller unmounts or navigates away.
 *  Pass `learningContext` to inject a pre-formatted background paragraph into the system prompt
 *  for every turn of the session — used by Q&A Forensics to anchor the chat to a specific exchange
 *  without sending the context wall as a user message.
 */
export async function streamChat(
  ticker: string,
  message: string,
  sessionId: string | null,
  callbacks: StreamChatCallbacks,
  signal?: AbortSignal,
  learningContext?: string,
): Promise<void> {
  const supabase = createSupabaseBrowserClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const response = await fetch(`${API_URL}/api/calls/${ticker}/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      message,
      session_id: sessionId,
      ...(learningContext ? { learning_context: learningContext } : {}),
    }),
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

  // Release the reader lock if the caller aborts mid-stream
  signal?.addEventListener("abort", () => { reader.cancel().catch(() => {}); });

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    if (signal?.aborted) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by double newlines
    const events = buffer.split("\n\n");
    // Keep the last (potentially incomplete) chunk in the buffer
    buffer = events.pop() ?? "";

    for (const event of events) {
      const dataLine = event
        .split("\n")
        .find((line) => line.startsWith("data: "));
      if (!dataLine) continue;

      const jsonStr = dataLine.slice("data: ".length);
      let parsed: { type: string; content?: string; session_id?: string; message?: string };
      try {
        parsed = JSON.parse(jsonStr);
      } catch {
        continue;
      }

      if (parsed.type === "token" && parsed.content !== undefined) {
        callbacks.onToken(parsed.content);
      } else if (parsed.type === "done" && parsed.session_id !== undefined) {
        callbacks.onDone(parsed.session_id);
      } else if (parsed.type === "error") {
        callbacks.onError(parsed.message ?? "Unknown error");
      }
    }
  }
}
