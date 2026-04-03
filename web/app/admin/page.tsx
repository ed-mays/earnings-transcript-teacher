/** Admin analytics dashboard — aggregated observability panels. Server component. */

import { createSupabaseServerClient } from "@/lib/supabase/server";

interface DailyCount {
  date: string;
  count: number;
}

interface DailyTurns {
  date: string;
  turns: number;
}

interface ChatData {
  daily: DailyTurns[];
  avg_turns_per_session: number;
}

interface ServiceTokens {
  input_tokens: number;
  output_tokens: number;
}

interface CostsData {
  by_service: Record<string, ServiceTokens>;
}

interface StageCount {
  stage: number;
  count: number;
}

interface FeynmanData {
  by_stage: StageCount[];
}

interface IngestionEntry {
  ticker: string;
  requested_at: string;
}

interface IngestionsData {
  ingestions: IngestionEntry[];
}

async function getSession() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session;
}

async function fetchSessions(): Promise<DailyCount[] | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) return null;

  const session = await getSession();
  if (!session) return null;

  try {
    const resp = await fetch(`${apiUrl}/admin/analytics/sessions`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      cache: "no-store",
    });
    if (!resp.ok) return null;
    return resp.json() as Promise<DailyCount[]>;
  } catch {
    return null;
  }
}

async function fetchFeynman(): Promise<FeynmanData | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) return null;

  const session = await getSession();
  if (!session) return null;

  try {
    const resp = await fetch(`${apiUrl}/admin/analytics/feynman`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      cache: "no-store",
    });
    if (!resp.ok) return null;
    return resp.json() as Promise<FeynmanData>;
  } catch {
    return null;
  }
}

async function fetchIngestions(): Promise<IngestionsData | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) return null;

  const session = await getSession();
  if (!session) return null;

  try {
    const resp = await fetch(`${apiUrl}/admin/analytics/ingestions`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      cache: "no-store",
    });
    if (!resp.ok) return null;
    return resp.json() as Promise<IngestionsData>;
  } catch {
    return null;
  }
}

async function fetchCosts(): Promise<CostsData | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) return null;

  const session = await getSession();
  if (!session) return null;

  try {
    const resp = await fetch(`${apiUrl}/admin/analytics/costs`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      cache: "no-store",
    });
    if (!resp.ok) return null;
    return resp.json() as Promise<CostsData>;
  } catch {
    return null;
  }
}

async function fetchChat(): Promise<ChatData | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) return null;

  const session = await getSession();
  if (!session) return null;

  try {
    const resp = await fetch(`${apiUrl}/admin/analytics/chat`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      cache: "no-store",
    });
    if (!resp.ok) return null;
    return resp.json() as Promise<ChatData>;
  } catch {
    return null;
  }
}

function AnalyticsCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h2>
      {children}
    </div>
  );
}

export default async function AdminAnalyticsPage() {
  const [sessions, chat, costs, feynman, ingestions] = await Promise.all([
    fetchSessions(),
    fetchChat(),
    fetchCosts(),
    fetchFeynman(),
    fetchIngestions(),
  ]);

  const totalSessions = sessions?.reduce((sum, row) => sum + row.count, 0) ?? 0;
  const totalTurns = chat?.daily.reduce((sum, row) => sum + row.turns, 0) ?? 0;

  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-12">
      <div className="mb-6 flex gap-4 text-sm">
        <a href="/admin/health" className="text-blue-600 hover:underline">
          System Health
        </a>
        <a href="/admin/ingest" className="text-blue-600 hover:underline">
          Ingest
        </a>
      </div>
      <h1 className="mb-8 text-3xl font-semibold text-foreground">Admin — Analytics</h1>

      <div className="grid gap-6 lg:grid-cols-2">
        <AnalyticsCard title={`Session Activity — last 30 days (${totalSessions} total)`}>
          {sessions === null ? (
            <p className="text-sm text-destructive">Unable to load session data.</p>
          ) : sessions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No sessions recorded yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-1.5 text-left font-medium text-muted-foreground">Date</th>
                  <th className="py-1.5 text-right font-medium text-muted-foreground">Sessions</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((row) => (
                  <tr key={row.date} className="border-b border-border">
                    <td className="py-1.5 text-foreground">{row.date}</td>
                    <td className="py-1.5 text-right tabular-nums text-foreground">{row.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </AnalyticsCard>

        <AnalyticsCard title="API Cost — last 30 days (tokens by service)">
          {costs === null ? (
            <p className="text-sm text-destructive">Unable to load cost data.</p>
          ) : Object.keys(costs.by_service).length === 0 ? (
            <p className="text-sm text-muted-foreground">No API calls recorded yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-1.5 text-left font-medium text-muted-foreground">Service</th>
                  <th className="py-1.5 text-right font-medium text-muted-foreground">Input</th>
                  <th className="py-1.5 text-right font-medium text-muted-foreground">Output</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(costs.by_service).map(([service, tokens]) => (
                  <tr key={service} className="border-b border-border">
                    <td className="py-1.5 capitalize text-foreground">{service}</td>
                    <td className="py-1.5 text-right tabular-nums text-foreground">
                      {tokens.input_tokens.toLocaleString()}
                    </td>
                    <td className="py-1.5 text-right tabular-nums text-foreground">
                      {tokens.output_tokens.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </AnalyticsCard>

        <AnalyticsCard
          title={`Chat Activity — last 30 days (${totalTurns} turns, avg ${chat?.avg_turns_per_session ?? 0} per session)`}
        >
          {chat === null ? (
            <p className="text-sm text-destructive">Unable to load chat data.</p>
          ) : chat.daily.length === 0 ? (
            <p className="text-sm text-muted-foreground">No chat turns recorded yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-1.5 text-left font-medium text-muted-foreground">Date</th>
                  <th className="py-1.5 text-right font-medium text-muted-foreground">Turns</th>
                </tr>
              </thead>
              <tbody>
                {chat.daily.map((row) => (
                  <tr key={row.date} className="border-b border-border">
                    <td className="py-1.5 text-foreground">{row.date}</td>
                    <td className="py-1.5 text-right tabular-nums text-foreground">{row.turns}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </AnalyticsCard>

        <AnalyticsCard title="Feynman Engagement — stage funnel, last 30 days">
          {feynman === null ? (
            <p className="text-sm text-destructive">Unable to load Feynman data.</p>
          ) : feynman.by_stage.length === 0 ? (
            <p className="text-sm text-muted-foreground">No Feynman sessions recorded yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-1.5 text-left font-medium text-muted-foreground">Stage</th>
                  <th className="py-1.5 text-right font-medium text-muted-foreground">Sessions</th>
                </tr>
              </thead>
              <tbody>
                {feynman.by_stage.map((row) => (
                  <tr key={row.stage} className="border-b border-border">
                    <td className="py-1.5 text-foreground">Stage {row.stage}</td>
                    <td className="py-1.5 text-right tabular-nums text-foreground">{row.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </AnalyticsCard>
        <AnalyticsCard title="Ingestion History — most recent 100 requests">
          {ingestions === null ? (
            <p className="text-sm text-destructive">Unable to load ingestion data.</p>
          ) : ingestions.ingestions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No ingestions recorded yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-1.5 text-left font-medium text-muted-foreground">Ticker</th>
                  <th className="py-1.5 text-right font-medium text-muted-foreground">Requested At</th>
                </tr>
              </thead>
              <tbody>
                {ingestions.ingestions.map((row, i) => (
                  <tr key={i} className="border-b border-border">
                    <td className="py-1.5 font-mono text-foreground">{row.ticker}</td>
                    <td className="py-1.5 text-right text-foreground">
                      {new Date(row.requested_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </AnalyticsCard>
      </div>
    </div>
  );
}
