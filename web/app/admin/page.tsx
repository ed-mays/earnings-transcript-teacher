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
    <div className="rounded-lg border border-zinc-200 bg-white p-5">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        {title}
      </h2>
      {children}
    </div>
  );
}

export default async function AdminAnalyticsPage() {
  const [sessions, chat] = await Promise.all([fetchSessions(), fetchChat()]);

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
      <h1 className="mb-8 text-3xl font-semibold text-zinc-900">Admin — Analytics</h1>

      <div className="grid gap-6 lg:grid-cols-2">
        <AnalyticsCard title={`Session Activity — last 30 days (${totalSessions} total)`}>
          {sessions === null ? (
            <p className="text-sm text-red-500">Unable to load session data.</p>
          ) : sessions.length === 0 ? (
            <p className="text-sm text-zinc-500">No sessions recorded yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-100">
                  <th className="py-1.5 text-left font-medium text-zinc-500">Date</th>
                  <th className="py-1.5 text-right font-medium text-zinc-500">Sessions</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((row) => (
                  <tr key={row.date} className="border-b border-zinc-50">
                    <td className="py-1.5 text-zinc-700">{row.date}</td>
                    <td className="py-1.5 text-right tabular-nums text-zinc-900">{row.count}</td>
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
            <p className="text-sm text-red-500">Unable to load chat data.</p>
          ) : chat.daily.length === 0 ? (
            <p className="text-sm text-zinc-500">No chat turns recorded yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-100">
                  <th className="py-1.5 text-left font-medium text-zinc-500">Date</th>
                  <th className="py-1.5 text-right font-medium text-zinc-500">Turns</th>
                </tr>
              </thead>
              <tbody>
                {chat.daily.map((row) => (
                  <tr key={row.date} className="border-b border-zinc-50">
                    <td className="py-1.5 text-zinc-700">{row.date}</td>
                    <td className="py-1.5 text-right tabular-nums text-zinc-900">{row.turns}</td>
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
