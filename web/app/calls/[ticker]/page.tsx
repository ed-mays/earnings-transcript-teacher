import Link from "next/link";
import { TranscriptBrowser } from "@/components/transcript/TranscriptBrowser";
import { MetadataPanel } from "@/components/transcript/MetadataPanel";
import type { CallDetail } from "@/components/transcript/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

/** Fetch call detail server-side; throws on error so Next.js renders the error boundary. */
async function fetchCallDetail(ticker: string): Promise<CallDetail | null> {
  if (!API_URL) throw new Error("NEXT_PUBLIC_API_URL is not configured");

  const res = await fetch(`${API_URL}/api/calls/${ticker}`, {
    next: { revalidate: 60 },
  });

  if (res.status === 404) return null;
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new Error(`API error ${res.status}: ${msg}`);
  }

  return res.json() as Promise<CallDetail>;
}

/** Transcript browser and metadata panel for a given ticker. */
export default async function TranscriptPage({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = await params;
  const call = await fetchCallDetail(ticker.toUpperCase());

  if (!call) {
    return (
      <div className="mx-auto w-full max-w-7xl px-6 py-12">
        <p className="text-sm text-zinc-500">
          No transcript found for <span className="font-semibold uppercase">{ticker}</span>.{" "}
          <Link href="/" className="underline hover:text-zinc-700">
            Back to library
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-8">
      {/* Header */}
      <div className="mb-6 flex items-baseline gap-3">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-900 uppercase">
          {call.ticker}
        </h1>
        {call.company_name && (
          <span className="text-lg text-zinc-500">{call.company_name}</span>
        )}
        {call.call_date && (
          <span className="ml-auto text-sm text-zinc-400">{call.call_date}</span>
        )}
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_360px]">
        {/* Left: transcript browser — client component */}
        <TranscriptBrowser ticker={call.ticker} call={call} />

        {/* Right: metadata panel — client component */}
        <div className="lg:sticky lg:top-6 lg:self-start">
          <MetadataPanel call={call} />
          <Link
            href={`/calls/${call.ticker}/learn`}
            className="mt-4 block w-full rounded-lg bg-zinc-900 px-4 py-2.5 text-center text-sm font-medium text-white transition-colors hover:bg-zinc-700"
          >
            Study with Feynman chat
          </Link>
        </div>
      </div>
    </div>
  );
}
