/** Server-side proxy for GET /admin/health — keeps ADMIN_SECRET_TOKEN off the client. */
import { NextResponse } from "next/server";

export async function GET(): Promise<NextResponse> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const adminToken = process.env.ADMIN_SECRET_TOKEN;

  if (!apiUrl || !adminToken) {
    return NextResponse.json(
      { error: "Server misconfiguration: NEXT_PUBLIC_API_URL or ADMIN_SECRET_TOKEN is not set" },
      { status: 500 }
    );
  }

  try {
    const resp = await fetch(`${apiUrl}/admin/health`, {
      headers: { "X-Admin-Token": adminToken },
      cache: "no-store",
    });

    const data: unknown = await resp.json();
    return NextResponse.json(data, { status: resp.status });
  } catch {
    return NextResponse.json({ error: "Failed to reach backend" }, { status: 502 });
  }
}
