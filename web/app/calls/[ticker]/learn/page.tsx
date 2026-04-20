import { permanentRedirect } from "next/navigation";

/** /learn is superseded by the consolidated guided-analysis view. Kept as a 308 redirect
 *  for a release or two so outstanding deep links (including ?topic=...) still resolve. */
export default async function LearnRedirect({
  params,
  searchParams,
}: {
  params: Promise<{ ticker: string }>;
  searchParams: Promise<{ topic?: string }>;
}) {
  const { ticker } = await params;
  const { topic } = await searchParams;
  const target = topic
    ? `/calls/${ticker}?topic=${encodeURIComponent(topic)}`
    : `/calls/${ticker}`;
  permanentRedirect(target);
}
