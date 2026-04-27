import Link from "next/link";
import { QAForensicsClient } from "@/components/qa-forensics/QAForensicsClient";
import type { QAForensicsResponse } from "@/components/transcript/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

async function fetchQAForensics(ticker: string): Promise<QAForensicsResponse | null> {
  if (!API_URL) throw new Error("NEXT_PUBLIC_API_URL is not configured");

  const res = await fetch(`${API_URL}/api/calls/${ticker}/qa-forensics`, {
    next: { revalidate: 300 },
  });

  if (res.status === 404) return null;
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new Error(`API error ${res.status}: ${msg}`);
  }

  return res.json() as Promise<QAForensicsResponse>;
}

/** Q&A Forensics learning mode for a single call. */
export default async function QAForensicsPage({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = await params;
  const upperTicker = ticker.toUpperCase();
  const data = await fetchQAForensics(upperTicker);

  if (!data) {
    return (
      <div className="mx-auto w-full max-w-7xl px-6 py-12">
        <p className="text-sm text-muted-foreground">
          No transcript found for{" "}
          <span className="font-semibold uppercase">{ticker}</span>.{" "}
          <Link href="/" className="underline hover:text-foreground">
            Back to library
          </Link>
        </p>
      </div>
    );
  }

  return <QAForensicsClient ticker={upperTicker} data={data} />;
}
