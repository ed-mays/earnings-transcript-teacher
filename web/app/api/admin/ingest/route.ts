/** Server-side proxy for POST /admin/ingest — verifies admin role, forwards JWT to FastAPI. */
import { requireAdminUser } from "@/lib/admin-auth";
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest): Promise<NextResponse> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;

  if (!apiUrl) {
    return NextResponse.json(
      { error: "Server misconfiguration: NEXT_PUBLIC_API_URL is not set" },
      { status: 500 }
    );
  }

  const authResult = await requireAdminUser();
  if (authResult instanceof NextResponse) return authResult;

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
        Authorization: `Bearer ${authResult.accessToken}`,
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
