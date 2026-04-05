"use client";

/** Shared "What this signals" section — three-state: content / error / fetch button. */

import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/button";
import remarkGfm from "remark-gfm";

interface SignalsSectionProps {
  /** Markdown content once loaded, or null if not yet fetched. */
  signals: string | null;
  /** Whether the stream is currently loading. */
  loading: boolean;
  /** Error message if the stream failed. */
  error: string | null;
  /** Called when the user clicks the fetch button. */
  onFetch: () => void;
  /** Button and heading label text. */
  label?: string;
  /** Color variant: "warning" uses amber tones; "muted" uses neutral tones. */
  variant?: "warning" | "muted";
  /** Extra top margin class — defaults to "mt-1" for inline use, "mt-3" for collapsible use. */
  topMargin?: string;
}

const WARNING_STYLES = {
  box: "bg-warning/10 border-warning/30",
  heading: "text-warning-foreground",
  text: "text-warning-foreground",
  border: "border-warning/40",
  button: "border-warning/30 bg-warning/10 text-warning-foreground hover:bg-warning/20",
};

const MUTED_STYLES = {
  box: "bg-muted/50 border",
  heading: "text-muted-foreground",
  text: "text-foreground/80",
  border: "border-muted",
  button: "border bg-muted/30 text-muted-foreground hover:bg-muted/60",
};

export function SignalsSection({
  signals,
  loading,
  error,
  onFetch,
  label = "📈 What this signals for investors",
  variant = "warning",
  topMargin = "mt-1",
}: SignalsSectionProps) {
  const s = variant === "muted" ? MUTED_STYLES : WARNING_STYLES;

  if (signals) {
    return (
      <div className={`${topMargin} rounded-md ${s.box} border px-3 py-2`}>
        <p className={`text-xs font-semibold uppercase tracking-wide ${s.heading} mb-1`}>
          {label}
        </p>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            p: ({ children }) => (
              <p className={`text-sm ${s.text} mb-1 last:mb-0`}>{children}</p>
            ),
            ul: ({ children }) => (
              <ul className={`list-disc list-inside text-sm ${s.text} space-y-2 mb-1`}>
                {children}
              </ul>
            ),
            ol: ({ children }) => (
              <ol className={`list-decimal list-inside text-sm ${s.text} space-y-2 mb-1`}>
                {children}
              </ol>
            ),
            li: ({ children }) => (
              <li className={`text-sm ${s.text} border-l-2 ${s.border} pl-2`}>{children}</li>
            ),
            strong: ({ children }) => (
              <strong className={`font-semibold ${s.text}`}>{children}</strong>
            ),
          }}
        >
          {signals}
        </ReactMarkdown>
      </div>
    );
  }

  if (error) {
    return <p className={`${topMargin} text-xs text-destructive`}>{error}</p>;
  }

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={onFetch}
      disabled={loading}
      className={`${topMargin} w-full ${s.button}`}
    >
      {loading ? "Analysing…" : label}
    </Button>
  );
}
