"use client";

import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ChatInput } from "@/components/chat/ChatInput";
import { ChatThread } from "@/components/chat/ChatThread";
import { streamChat, type ChatMessage } from "@/lib/chat";
import { cn } from "@/lib/utils";
import type { ChatContext } from "./types";

interface ChatPanelProps {
  ticker: string;
  context: ChatContext | null;
  onClose: () => void;
  /** When true and a context seed is present, send the seeded message
   *  immediately on mount instead of pre-filling the input. Used by
   *  Q&A Forensics chip clicks where the chip text IS the message. */
  autoSend?: boolean;
}

/** Right-side chat panel wired to the streaming Feynman chat endpoint. */
export function ChatPanel({ ticker, context, onClose, autoSend = false }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const hasAutoSentRef = useRef(false);

  const seedValue = context ? contextToPrompt(context) : "";
  // When auto-sending, we fire the seed via the effect below — keep the
  // visible input empty so the textarea is a clean slate for follow-ups.
  const inputInitialValue = autoSend ? "" : seedValue;

  async function handleSend(message: string) {
    const controller = new AbortController();
    abortRef.current = controller;
    setMessages((m) => [...m, { role: "user", content: message }]);
    setIsStreaming(true);
    setStreamingContent("");

    let accumulated = "";
    try {
      await streamChat(
        ticker,
        message,
        sessionId,
        {
          onToken: (token) => {
            accumulated += token;
            setStreamingContent(accumulated);
          },
          onDone: (newSessionId) => {
            setSessionId(newSessionId);
            setMessages((m) => [...m, { role: "assistant", content: accumulated }]);
            setStreamingContent("");
            setIsStreaming(false);
          },
          onError: () => {
            setIsStreaming(false);
            setStreamingContent("");
          },
        },
        controller.signal,
      );
    } catch {
      setIsStreaming(false);
    }
  }

  function handleAbort() {
    abortRef.current?.abort();
    setIsStreaming(false);
  }

  function handleNewSession() {
    abortRef.current?.abort();
    setMessages([]);
    setStreamingContent("");
    setSessionId(null);
    setIsStreaming(false);
  }

  useEffect(() => {
    if (autoSend && seedValue && !hasAutoSentRef.current) {
      hasAutoSentRef.current = true;
      handleSend(seedValue);
    }
    // handleSend is intentionally not in deps — it's recreated each render
    // and the ref guard ensures we only fire once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoSend, seedValue]);

  return (
    <aside
      className={cn(
        "flex h-full w-full flex-col bg-background",
        "lg:w-[400px] lg:border-l",
      )}
      aria-label="Learning chat"
    >
      <header className="flex items-center justify-between border-b px-4 py-3">
        <h2 className="text-sm font-semibold">Discuss</h2>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={handleNewSession}>
            New session
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            aria-label="Close chat panel"
          >
            <X className="h-4 w-4" aria-hidden />
          </Button>
        </div>
      </header>
      <div className="flex min-h-0 flex-1 flex-col">
        <ChatThread messages={messages} streamingContent={streamingContent} />
      </div>
      <div className="p-4">
        <ChatInput
          onSend={handleSend}
          onAbort={handleAbort}
          isStreaming={isStreaming}
          initialValue={inputInitialValue}
        />
      </div>
    </aside>
  );
}

function contextToPrompt(context: ChatContext): string {
  switch (context.type) {
    case "evasion":
      return `Help me understand this evasion: ${context.metadata ?? ""}\n\n${context.text}`.trim();
    case "term":
      return `Explain "${context.text}" in context${context.metadata ? `: ${context.metadata}` : ""}.`;
    case "guidance":
      return `What should I take away from this guidance point? ${context.text}`;
    case "qa-forensics":
      // Seed is fully constructed by QAForensicsClient — pass through verbatim
      // so Stage 1 of the Feynman flow gets the user's own judgment as context.
      return context.text;
    default:
      return context.text;
  }
}
