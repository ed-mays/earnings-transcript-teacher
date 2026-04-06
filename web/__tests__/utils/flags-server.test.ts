import { vi, describe, it, expect, beforeEach } from "vitest";
import { getFeatureFlags } from "@/lib/flags-server";

describe("getFeatureFlags", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns parsed flags on success", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ chat_enabled: true, ingestion_enabled: false }),
    } as Response);

    const flags = await getFeatureFlags();
    expect(flags).toEqual({ chat_enabled: true, ingestion_enabled: false });
  });

  it("returns empty object on fetch error", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new Error("network down"));
    const flags = await getFeatureFlags();
    expect(flags).toEqual({});
  });

  it("returns empty object on non-ok response", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: false,
      status: 503,
    } as Response);
    const flags = await getFeatureFlags();
    expect(flags).toEqual({});
  });
});
