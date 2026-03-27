/** Feynman-style learning chat for a given ticker's transcript. */
export default async function LearnPage({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = await params;

  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-12">
      <h1 className="mb-2 text-3xl font-semibold text-zinc-900">
        Learn: <span className="uppercase">{ticker}</span>
      </h1>
      <p className="text-zinc-500">Feynman chat — coming soon.</p>
    </div>
  );
}
