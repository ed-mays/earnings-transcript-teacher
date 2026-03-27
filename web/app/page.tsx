import { createSupabaseServerClient } from "@/lib/supabase/server";

/** Library page — lists all ingested earnings call transcripts. */
export default async function LibraryPage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-12">
      <h1 className="mb-2 text-3xl font-semibold text-zinc-900">
        Transcript Library
      </h1>
      <p className="text-zinc-500">
        Welcome, {user?.email}. Your ingested earnings transcripts will appear
        here.
      </p>
    </div>
  );
}
