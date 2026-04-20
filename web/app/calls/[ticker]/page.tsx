import Link from "next/link";
import { GuidedAnalysisView } from "./GuidedAnalysisView";
import type { CallDetail } from "@/components/transcript/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface AdjacentCallInfo {
  ticker: string;
  fiscal_quarter?: string | null;
  company_name?: string | null;
  call_date?: string | null;
}

interface AdjacentCalls {
  prev: AdjacentCallInfo | null;
  next: AdjacentCallInfo | null;
}

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
  if (!API_URL) return { prev: null, next: null };
  try {
    const res = await fetch(`${API_URL}/api/calls/${ticker}/adjacent`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return { prev: null, next: null };
    return res.json() as Promise<AdjacentCalls>;
  } catch {
    return { prev: null, next: null };
  }
}

/** Guided analysis view for a single earnings call. */
export default async function CallPage({
  params,
  searchParams,
}: {
  params: Promise<{ ticker: string }>;
  searchParams: Promise<{ topic?: string }>;
}) {
  const { ticker } = await params;
  const { topic } = await searchParams;
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

  return <GuidedAnalysisView call={call} adjacent={adjacent} initialTopic={topic} />;
}
