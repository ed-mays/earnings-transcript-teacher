"use client";

import { useRef, useState } from "react";
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
}

/** Right-side chat panel wired to the streaming Feynman chat endpoint. */
export function ChatPanel({ ticker, context, onClose }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const initialValue = context ? contextToPrompt(context) : "";

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
          initialValue={initialValue}
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
