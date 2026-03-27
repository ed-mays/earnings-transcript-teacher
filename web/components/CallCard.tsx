import Link from "next/link";

export interface CallSummary {
  ticker: string;
  company_name: string | null;
  call_date: string | null;
  industry: string | null;
}

interface CallCardProps {
  call: CallSummary;
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
    </Link>
  );
}
