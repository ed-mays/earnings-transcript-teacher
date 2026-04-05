/** Admin health page — shows DB, env var, and external API status. Server component. */

import { createSupabaseServerClient } from "@/lib/supabase/server";
import { Card } from "@/components/ui/card";

interface DbStatus {
  connected: boolean;
}

interface ServiceStatus {
  reachable: boolean;
}

interface HealthData {
  db: DbStatus;
  env_vars: Record<string, boolean>;
  external_apis: Record<string, ServiceStatus>;
}

const ENV_VAR_LABELS: Record<string, string> = {
  VOYAGE_API_KEY: "Voyage AI API Key",
  PERPLEXITY_API_KEY: "Perplexity API Key",
  MODAL_TOKEN_ID: "Modal Token ID",
  SUPABASE_JWT_SECRET: "Supabase JWT Secret",
};

async function fetchHealth(): Promise<HealthData | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) return null;

  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) return null;

  try {
    const resp = await fetch(`${apiUrl}/admin/health`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      cache: "no-store",
    });
    if (!resp.ok) return null;
    return resp.json() as Promise<HealthData>;
  } catch {
    return null;
  }
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block h-3 w-3 flex-shrink-0 rounded-full ${ok ? "bg-success" : "bg-destructive"}`}
    />
  );
}

function StatusRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center gap-3 py-1.5">
      <StatusDot ok={ok} />
      <span className="text-sm text-foreground">{label}</span>
    </div>
  );
}

function StatusCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="p-5 gap-0">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h2>
      {children}
    </Card>
  );
}

export default async function AdminHealthPage() {
  const health = await fetchHealth();

  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-12">
      <h1 className="mb-8 text-3xl font-semibold text-foreground">Admin — System Health</h1>

      {health === null ? (
        <p className="text-destructive">Unable to fetch health data. Check server configuration.</p>
      ) : (
        <div className="grid gap-6 sm:grid-cols-3">
          <StatusCard title="Database">
            <StatusRow label="Connected" ok={health.db.connected} />
          </StatusCard>

          <StatusCard title="Environment Variables">
            {Object.entries(health.env_vars).map(([key, present]) => (
              <StatusRow key={key} label={ENV_VAR_LABELS[key] ?? key} ok={present} />
            ))}
          </StatusCard>

          <StatusCard title="External APIs">
            {Object.entries(health.external_apis).map(([name, status]) => (
              <StatusRow
                key={name}
                label={name.charAt(0).toUpperCase() + name.slice(1)}
                ok={status.reachable}
              />
            ))}
          </StatusCard>
        </div>
      )}
    </div>
  );
}
