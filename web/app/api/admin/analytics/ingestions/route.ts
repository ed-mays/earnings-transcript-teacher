/** Server-side proxy for GET /admin/analytics/ingestions — verifies admin role, forwards JWT to FastAPI. */
import { requireAdminUser } from "@/lib/admin-auth";
import { NextResponse } from "next/server";

export async function GET(): Promise<NextResponse> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;

  if (!apiUrl) {
    return NextResponse.json(
      { error: "Server misconfiguration: NEXT_PUBLIC_API_URL is not set" },
      { status: 500 }
    );
  }

  const authResult = await requireAdminUser();
  if (authResult instanceof NextResponse) return authResult;

  try {
    const resp = await fetch(`${apiUrl}/admin/analytics/ingestions`, {
      headers: { Authorization: `Bearer ${authResult.accessToken}` },
      cache: "no-store",
    });
    const data: unknown = await resp.json();
    return NextResponse.json(data, { status: resp.status });
  } catch {
    return NextResponse.json({ error: "Failed to reach backend" }, { status: 502 });
  }
}
