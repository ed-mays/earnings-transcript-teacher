/** Server-side proxy for POST /admin/ingest — email guard + JWT forwarded to FastAPI. */
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest): Promise<NextResponse> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const adminEmail = process.env.ADMIN_EMAIL;

  if (!apiUrl) {
    return NextResponse.json(
      { error: "Server misconfiguration: NEXT_PUBLIC_API_URL is not set" },
      { status: 500 }
    );
  }

  if (!adminEmail) {
    return NextResponse.json(
      { error: "Server misconfiguration: ADMIN_EMAIL is not set" },
      { status: 500 }
    );
  }

  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  if (session.user.email !== adminEmail) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }

  try {
    const resp = await fetch(`${apiUrl}/admin/ingest`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    const data: unknown = await resp.json();
    return NextResponse.json(data, { status: resp.status });
  } catch {
    return NextResponse.json({ error: "Failed to reach backend" }, { status: 502 });
  }
}
