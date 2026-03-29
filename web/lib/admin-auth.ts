import { createSupabaseServerClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

/** Verifies the request is from an authenticated admin user.
 *
 * Uses getUser() (server-side JWT validation) rather than getSession() (cookie cache)
 * to prevent session spoofing. Returns the user ID and access token on success,
 * or a NextResponse error (401/403) on failure.
 */
export async function requireAdminUser(): Promise<
  { userId: string; accessToken: string } | NextResponse
> {
  const supabase = await createSupabaseServerClient();

  // getUser() contacts the Supabase auth server — more secure than getSession()
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const { data: profile } = await supabase
    .from("profiles")
    .select("role")
    .eq("id", user.id)
    .single();

  if (profile?.role !== "admin") {
    return NextResponse.json({ error: "Admin role required" }, { status: 403 });
  }

  // getSession() is safe here — identity already confirmed via getUser() above
  const {
    data: { session },
  } = await supabase.auth.getSession();

  return { userId: user.id, accessToken: session?.access_token ?? "" };
}
