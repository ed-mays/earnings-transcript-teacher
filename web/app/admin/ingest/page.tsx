/** Admin page for triggering transcript ingestion. */
export default function AdminIngestPage() {
  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-12">
      <div className="mb-6">
        <a href="/admin/health" className="text-sm text-blue-600 hover:underline">
          System Health →
        </a>
      </div>
      <h1 className="mb-2 text-3xl font-semibold text-zinc-900">
        Admin — Ingest
      </h1>
      <p className="text-zinc-500">Ingestion form — coming soon.</p>
    </div>
  );
}
