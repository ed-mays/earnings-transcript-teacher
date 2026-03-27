import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { CallList } from "@/components/CallList";

/** Library page — lists all ingested earnings call transcripts. */
export default async function LibraryPage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth/sign-in");
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-12">
      <h1 className="mb-2 text-3xl font-semibold text-zinc-900">
        Transcript Library
      </h1>
      <p className="mb-8 text-zinc-500">
        Select a transcript to study.
      </p>
      <CallList />
    </div>
  );
}
