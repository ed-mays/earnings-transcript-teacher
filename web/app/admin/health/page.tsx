/** Admin health page — shows DB, env var, and external API status. Server component. */

interface DbStatus {
  connected: boolean;
  schema_version: number;
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
  const adminToken = process.env.ADMIN_SECRET_TOKEN;

  if (!apiUrl || !adminToken) return null;

  try {
    const resp = await fetch(`${apiUrl}/admin/health`, {
      headers: { "X-Admin-Token": adminToken },
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
      className={`inline-block h-3 w-3 flex-shrink-0 rounded-full ${ok ? "bg-green-500" : "bg-red-500"}`}
    />
  );
}

function StatusRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center gap-3 py-1.5">
      <StatusDot ok={ok} />
      <span className="text-sm text-zinc-700">{label}</span>
    </div>
  );
}

function StatusCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">
        {title}
      </h2>
      {children}
    </div>
  );
}

export default async function AdminHealthPage() {
  const health = await fetchHealth();

  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-12">
      <div className="mb-6">
        <a href="/admin/ingest" className="text-sm text-blue-600 hover:underline">
          ← Admin Ingest
        </a>
      </div>
      <h1 className="mb-8 text-3xl font-semibold text-zinc-900">Admin — System Health</h1>

      {health === null ? (
        <p className="text-red-500">Unable to fetch health data. Check server configuration.</p>
      ) : (
        <div className="grid gap-6 sm:grid-cols-3">
          <StatusCard title="Database">
            <StatusRow label="Connected" ok={health.db.connected} />
            <StatusRow
              label={`Schema v${health.db.schema_version}`}
              ok={health.db.connected}
            />
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
