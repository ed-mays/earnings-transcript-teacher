"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "@/lib/chat";
import { Button } from "@/components/ui/button";

interface ChatThreadProps {
  messages: ChatMessage[];
  streamingContent: string;
  suggestions?: string[];
  loadingSuggestions?: boolean;
  onSuggestionClick?: (suggestion: string) => void;
}

/** Renders the full conversation history plus any in-progress streamed assistant response. */
export function ChatThread({ messages, streamingContent, suggestions, loadingSuggestions, onSuggestionClick }: ChatThreadProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const [fadingOut, setFadingOut] = useState<string | null>(null);

  function handleScroll() {
    const el = scrollContainerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    const near = distanceFromBottom < 100;
    isNearBottomRef.current = near;
    setIsNearBottom(near);
  }

  function scrollToBottom() {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    isNearBottomRef.current = true;
    setIsNearBottom(true);
  }

  useEffect(() => {
    if (isNearBottomRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, streamingContent]);

  function handleSuggestionClick(suggestion: string) {
    setFadingOut(suggestion);
    setTimeout(() => onSuggestionClick?.(suggestion), 200);
  }

  if (messages.length === 0 && !streamingContent) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-6">
        <p className="text-sm text-muted-foreground">
          Ask a question about this earnings call to get started.
        </p>
        {loadingSuggestions ? (
          <div className="flex flex-wrap justify-center gap-2">
            <div className="animate-pulse rounded-full bg-muted px-4 py-2 text-sm text-muted-foreground">
              Loading suggested starter questions…
            </div>
          </div>
        ) : suggestions && suggestions.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
            {suggestions.map((suggestion) => (
              <Button
                key={suggestion}
                variant="outline"
                onClick={() => handleSuggestionClick(suggestion)}
                className={`h-auto whitespace-normal px-4 py-3 text-left active:scale-[0.98] ${
                  fadingOut === suggestion ? "opacity-0 scale-95" : ""
                }`}
              >
                {suggestion}
              </Button>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className="relative flex flex-1 flex-col min-h-0">
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex flex-1 flex-col gap-4 overflow-y-auto px-1 py-2"
      >
        {messages.map((msg, i) => (
          <MessageBubble key={i} role={msg.role} content={msg.content} />
        ))}
        {streamingContent && (
          <MessageBubble role="assistant" content={streamingContent} streaming />
        )}
        <div ref={bottomRef} />
      </div>
      {streamingContent && !isNearBottom && (
        <Button
          size="sm"
          onClick={scrollToBottom}
          className="absolute bottom-2 left-1/2 -translate-x-1/2 rounded-full shadow-md"
        >
          ↓ New messages
        </Button>
      )}
    </div>
  );
}

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

function MessageBubble({ role, content, streaming = false }: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[90%] sm:max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-primary text-primary-foreground whitespace-pre-wrap"
            : "bg-muted text-foreground"
        }`}
      >
        {isUser ? (
          content
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              ul: ({ children }) => <ul className="mb-2 list-disc list-inside space-y-0.5 last:mb-0">{children}</ul>,
              ol: ({ children }) => <ol className="mb-2 list-decimal list-inside space-y-0.5 last:mb-0">{children}</ol>,
              li: ({ children }) => <li>{children}</li>,
              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
              em: ({ children }) => <em className="italic">{children}</em>,
              code: ({ children }) => <code className="rounded bg-background/50 px-1 py-0.5 font-mono text-xs">{children}</code>,
              pre: ({ children }) => <pre className="mb-2 overflow-x-auto rounded bg-background/50 p-2 font-mono text-xs last:mb-0">{children}</pre>,
            }}
          >
            {content}
          </ReactMarkdown>
        )}
        {streaming && (
          <span className="ml-1 inline-block h-3 w-0.5 animate-pulse bg-current" />
        )}
      </div>
    </div>
  );
}
