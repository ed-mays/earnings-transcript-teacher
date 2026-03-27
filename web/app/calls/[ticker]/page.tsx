/** Transcript browser and metadata panel for a given ticker. */
export default async function TranscriptPage({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = await params;

  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-12">
      <h1 className="mb-2 text-3xl font-semibold text-zinc-900 uppercase">
        {ticker}
      </h1>
      <p className="text-zinc-500">
        Transcript browser and metadata panel — coming soon.
      </p>
    </div>
  );
}
