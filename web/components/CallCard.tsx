import Link from "next/link";

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
  low: "bg-green-50 text-green-700",
  medium: "bg-amber-50 text-amber-700",
  high: "bg-red-50 text-red-700",
};

function sentimentStyle(sentiment: string): string {
  const lower = sentiment.toLowerCase();
  if (lower.includes("bullish") || lower.includes("positive")) {
    return "bg-green-50 text-green-700";
  }
  if (lower.includes("bearish") || lower.includes("negative")) {
    return "bg-red-50 text-red-700";
  }
  return "bg-zinc-100 text-zinc-600";
}

/** Card displaying summary metadata for a single earnings call. */
export function CallCard({ call }: CallCardProps) {
  return (
    <Link
      href={`/calls/${call.ticker}`}
      className="block rounded-xl border border-zinc-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md focus:outline-none focus:ring-2 focus:ring-zinc-500 focus:ring-offset-2"
    >
      <div className="flex items-start justify-between gap-4">
        <span className="text-2xl font-bold tracking-tight text-zinc-900">
          {call.ticker}
        </span>
        {call.call_date && (
          <span className="shrink-0 text-sm text-zinc-400">{call.call_date}</span>
        )}
      </div>
      {call.company_name && (
        <p className="mt-1 text-sm font-medium text-zinc-700">
          {call.company_name}
        </p>
      )}
      {call.industry && (
        <span className="mt-3 inline-block rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs text-zinc-600">
          {call.industry}
        </span>
      )}
      {(call.evasion_level || call.overall_sentiment) && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {call.overall_sentiment && (
            <span
              className={`inline-block rounded-full px-2.5 py-0.5 text-xs ${sentimentStyle(call.overall_sentiment)}`}
            >
              {call.overall_sentiment}
            </span>
          )}
          {call.evasion_level && (
            <span
              className={`inline-block rounded-full px-2.5 py-0.5 text-xs ${EVASION_STYLES[call.evasion_level] ?? "bg-zinc-100 text-zinc-600"}`}
            >
              {call.evasion_level} evasion
            </span>
          )}
        </div>
      )}
      {call.top_strategic_shift && (
        <p className="mt-2 truncate text-xs text-zinc-400">
          {call.top_strategic_shift}
        </p>
      )}
    </Link>
  );
}
