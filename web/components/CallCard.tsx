import Link from "next/link";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export interface CallSummary {
  ticker: string;
  company_name: string | null;
  call_date: string | null;
  industry: string | null;
  evasion_level: "low" | "medium" | "high" | null;
  overall_sentiment: string | null;
  top_strategic_shift: string | null;
}

interface CallCardProps {
  call: CallSummary;
}

const EVASION_STYLES: Record<string, string> = {
  low: "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  medium: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  high: "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

function sentimentStyle(sentiment: string): string {
  const lower = sentiment.toLowerCase();
  if (lower.includes("bullish") || lower.includes("positive")) {
    return "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400";
  }
  if (lower.includes("bearish") || lower.includes("negative")) {
    return "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400";
  }
  return "";
}

/** Card displaying summary metadata for a single earnings call. */
export function CallCard({ call }: CallCardProps) {
  return (
    <Link
      href={`/calls/${call.ticker}`}
      className="block transition-shadow hover:shadow-md focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 rounded-xl"
    >
      <Card className="p-6 gap-2 shadow-sm cursor-pointer h-full">
        <div className="flex items-start justify-between gap-4">
          <span className="text-2xl font-bold tracking-tight text-foreground">
            {call.ticker}
          </span>
          {call.call_date && (
            <span className="shrink-0 text-sm text-muted-foreground">{call.call_date}</span>
          )}
        </div>
        {call.company_name && (
          <p className="text-sm font-medium text-foreground/80">
            {call.company_name}
          </p>
        )}
        {call.industry && (
          <div>
            <Badge variant="secondary" className="rounded-full">
              {call.industry}
            </Badge>
          </div>
        )}
        {(call.evasion_level || call.overall_sentiment) && (
          <div className="flex flex-wrap gap-1.5">
            {call.overall_sentiment && (
              <span
                className={`inline-block rounded-full px-2.5 py-0.5 text-xs ${sentimentStyle(call.overall_sentiment) || "bg-muted text-muted-foreground"}`}
              >
                {call.overall_sentiment}
              </span>
            )}
            {call.evasion_level && (
              <span
                className={`inline-block rounded-full px-2.5 py-0.5 text-xs ${EVASION_STYLES[call.evasion_level] ?? "bg-muted text-muted-foreground"}`}
              >
                {call.evasion_level} evasion
              </span>
            )}
          </div>
        )}
        {call.top_strategic_shift && (
          <p className="truncate text-xs text-muted-foreground">
            {call.top_strategic_shift}
          </p>
        )}
      </Card>
    </Link>
  );
}
