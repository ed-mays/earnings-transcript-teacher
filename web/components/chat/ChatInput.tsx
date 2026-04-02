"use client";

import { useRef, useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

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
    <div className="flex items-end gap-2 border-t border pt-4">
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isStreaming}
        rows={3}
        placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
        className="flex-1 resize-none"
      />
      <Button
        onClick={handleSubmit}
        disabled={isStreaming || !value.trim()}
        className="mb-0.5"
      >
        {isStreaming ? "…" : "Send"}
      </Button>
    </div>
  );
}
