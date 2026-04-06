/**
 * Server-side helper to fetch all feature flags from the API.
 * Returns an empty object on any error so the app always boots.
 * Use in server components and layouts only.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export async function getFeatureFlags(): Promise<Record<string, boolean>> {
  if (!API_URL) {
    return {};
  }
  try {
    const response = await fetch(`${API_URL}/flags`, { cache: "no-store" });
    if (!response.ok) {
      return {};
    }
    return response.json() as Promise<Record<string, boolean>>;
  } catch {
    return {};
  }
}
