import { render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { CallList } from "@/components/CallList";
import { callSummaries } from "../utils/fixtures";

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from "@/lib/api";
const mockApi = api as unknown as { get: ReturnType<typeof vi.fn> };

describe("CallList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows 6 skeletons while loading", () => {
    mockApi.get.mockReturnValue(new Promise(() => {})); // never resolves
    render(<CallList />);
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBe(6);
  });

  it("shows error message when API rejects", async () => {
    mockApi.get.mockRejectedValue(new Error("Network error"));
    render(<CallList />);
    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  it("shows empty state when API returns empty array", async () => {
    mockApi.get.mockResolvedValue([]);
    render(<CallList />);
    await waitFor(() => {
      expect(screen.getByText("No transcripts yet")).toBeInTheDocument();
    });
  });

  it("renders a card for each returned call", async () => {
    mockApi.get.mockResolvedValue(callSummaries);
    render(<CallList />);
    await waitFor(() => {
      expect(screen.getByText("AAPL")).toBeInTheDocument();
      expect(screen.getByText("MSFT")).toBeInTheDocument();
    });
  });
});
