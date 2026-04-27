import { CallTabs } from "./CallTabs";

/** Shared layout for /calls/[ticker] and its sub-routes. Provides the section
 *  tab nav (Transcript / Q&A Forensics) and a flex-1 wrapper so child views
 *  fill the remaining viewport. */
export default async function CallLayout({
  params,
  children,
}: {
  params: Promise<{ ticker: string }>;
  children: React.ReactNode;
}) {
  const { ticker } = await params;
  const upperTicker = ticker.toUpperCase();
  return (
    <div className="flex h-[calc(100dvh-var(--nav-height))] min-h-0 w-full flex-col">
      <CallTabs ticker={upperTicker} />
      <div className="min-h-0 flex-1">{children}</div>
    </div>
  );
}
