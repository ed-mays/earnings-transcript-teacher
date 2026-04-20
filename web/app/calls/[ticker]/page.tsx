import Link from "next/link";
import { TranscriptBrowser } from "@/components/transcript/TranscriptBrowser";
import { MetadataPanel } from "@/components/transcript/MetadataPanel";
import { CallBriefPanel } from "@/components/transcript/CallBriefPanel";
import { Card } from "@/components/ui/card";
import type { CallDetail } from "@/components/transcript/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

type AdjacentCallInfo = {
  ticker: string
  fiscal_quarter?: string | null
  company_name?: string | null
  call_date?: string | null
}

type AdjacentCalls = {
  prev: AdjacentCallInfo | null
  next: AdjacentCallInfo | null
}

/** Fetch call detail server-side; throws on error so Next.js renders the error boundary. */
async function fetchCallDetail(ticker: string): Promise<CallDetail | null> {
  if (!API_URL) throw new Error("NEXT_PUBLIC_API_URL is not configured");

  const res = await fetch(`${API_URL}/api/calls/${ticker}`, {
    next: { revalidate: 300 },
  });

  if (res.status === 404) return null;
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new Error(`API error ${res.status}: ${msg}`);
  }

  return res.json() as Promise<CallDetail>;
}

async function fetchAdjacentCalls(ticker: string): Promise<AdjacentCalls> {
  if (!API_URL) return { prev: null, next: null }
  try {
    const res = await fetch(`${API_URL}/api/calls/${ticker}/adjacent`, {
      next: { revalidate: 300 },
    })
    if (!res.ok) return { prev: null, next: null }
    return res.json() as Promise<AdjacentCalls>
  } catch {
    return { prev: null, next: null }
  }
}

/** Transcript browser and metadata panel for a given ticker. */
export default async function TranscriptPage({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = await params;
  const upperTicker = ticker.toUpperCase();
  const [call, adjacent] = await Promise.all([
    fetchCallDetail(upperTicker),
    fetchAdjacentCalls(upperTicker),
  ]);

  if (!call) {
    return (
      <div className="mx-auto w-full max-w-7xl px-6 py-12">
        <p className="text-sm text-muted-foreground">
          No transcript found for <span className="font-semibold uppercase">{ticker}</span>.{" "}
          <Link href="/" className="underline hover:text-foreground">
            Back to library
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-8 lg:flex lg:h-[calc(100dvh-var(--nav-height))] lg:flex-col lg:overflow-hidden lg:py-0">
      {/* Header */}
      <div className="mb-6 flex items-center gap-3 lg:mb-0 lg:shrink-0 lg:py-6">
        <h1 className="text-3xl font-bold tracking-tight text-foreground uppercase">
          {call.ticker}
        </h1>
        {call.company_name && (
          <span className="text-lg text-muted-foreground">{call.company_name}</span>
        )}
        <div className="ml-auto flex items-center gap-4 text-sm text-muted-foreground">
          {adjacent.prev && (
            <Link href={`/calls/${adjacent.prev.ticker}`} className="hover:text-foreground">
              ← {adjacent.prev.ticker}
            </Link>
          )}
          {call.call_date && <span>{call.call_date}</span>}
          {adjacent.next && (
            <Link href={`/calls/${adjacent.next.ticker}`} className="hover:text-foreground">
              {adjacent.next.ticker} →
            </Link>
          )}
        </div>
      </div>

      {/* Call brief — shown above columns on mobile only */}
      {call.brief && (
        <div className="lg:hidden">
          <CallBriefPanel
            brief={call.brief}
            takeaways={call.takeaways}
            misconceptions={call.misconceptions}
            signal_strip={call.signal_strip ?? null}
          />
        </div>
      )}

      {/* Two-column layout */}
      <div className="flex flex-col gap-6 lg:flex-1 lg:min-h-0 lg:flex-row lg:gap-0 lg:overflow-hidden">
        {/* Left: call brief + transcript browser — client component */}
        <div className="lg:min-w-0 lg:flex-1 lg:overflow-y-auto lg:py-6">
          {/* Call brief — inside scroll area on desktop */}
          {call.brief && (
            <div className="mb-6 hidden lg:block">
              <CallBriefPanel
                brief={call.brief}
                takeaways={call.takeaways}
                misconceptions={call.misconceptions}
                signal_strip={call.signal_strip ?? null}
              />
            </div>
          )}
          <TranscriptBrowser ticker={call.ticker} call={call} />
        </div>

        {/* Right: metadata panel — client component */}
        <div className="lg:w-[360px] lg:shrink-0 lg:overflow-y-auto lg:border-l lg:py-6 lg:pl-6">
          <MetadataPanel call={call} />
          <Link href={`/calls/${call.ticker}/learn`} className="mt-4 block group">
            <Card className="p-4 transition-colors group-hover:bg-muted">
              <p className="text-sm font-semibold text-foreground">Study the annotated transcript</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Toggle guidance, evasion, sentiment, and term layers — then chat about any passage.
              </p>
            </Card>
          </Link>
        </div>
      </div>
    </div>
  );
}
