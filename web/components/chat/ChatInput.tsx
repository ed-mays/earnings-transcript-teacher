"use client";

import { useRef, useState } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  isStreaming: boolean;
  initialValue?: string;
}

/** Textarea with send button. Submits on Enter; Shift+Enter inserts a newline. */
export function ChatInput({ onSend, isStreaming, initialValue = "" }: ChatInputProps) {
  const [value, setValue] = useState(initialValue);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleSubmit() {
    const trimmed = value.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setValue("");
    textareaRef.current?.focus();
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <div className="flex items-end gap-2 border-t border-zinc-200 pt-4">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isStreaming}
        rows={3}
        placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
        className="flex-1 resize-none rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 focus:border-zinc-500 focus:outline-none disabled:opacity-50"
      />
      <button
        onClick={handleSubmit}
        disabled={isStreaming || !value.trim()}
        className="mb-0.5 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {isStreaming ? "…" : "Send"}
      </button>
    </div>
  );
}
