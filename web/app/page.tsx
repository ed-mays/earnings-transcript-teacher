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
      <h1 className="mb-2 text-3xl font-semibold text-foreground">
        Transcript Library
      </h1>
      <p className="mb-8 text-muted-foreground">
        Browse earnings call transcripts and study them interactively
      </p>
      <CallList />
    </div>
  );
}
