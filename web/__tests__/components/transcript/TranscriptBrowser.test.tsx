import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { TranscriptBrowser } from "@/components/transcript/TranscriptBrowser";
import { callDetail, spansResponse } from "../../utils/fixtures";

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from "@/lib/api";
const mockApi = api as { get: ReturnType<typeof vi.fn> };

describe("TranscriptBrowser", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows skeleton while loading on mount", () => {
    mockApi.get.mockReturnValue(new Promise(() => {})); // never resolves
    render(<TranscriptBrowser ticker="AAPL" call={callDetail} />);
    expect(document.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });

  it("shows error message when API rejects", async () => {
    mockApi.get.mockRejectedValue(new Error("Failed to load transcript."));
    render(<TranscriptBrowser ticker="AAPL" call={callDetail} />);
    await waitFor(() => {
      expect(screen.getByText("Failed to load transcript.")).toBeInTheDocument();
    });
  });

  it("renders span text blocks on success", async () => {
    mockApi.get.mockResolvedValue(spansResponse);
    render(<TranscriptBrowser ticker="AAPL" call={callDetail} />);
    await waitFor(() => {
      expect(
        screen.getByText("We are pleased to report record services revenue.")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Can you elaborate on the China situation?")
      ).toBeInTheDocument();
    });
  });

  it("calls the API with section=prepared when Prepared filter is clicked", async () => {
    mockApi.get.mockResolvedValue(spansResponse);
    render(<TranscriptBrowser ticker="AAPL" call={callDetail} />);
    await waitFor(() => screen.getByText("Prepared"));
    await userEvent.click(screen.getByText("Prepared"));
    await waitFor(() => {
      const lastCall = mockApi.get.mock.calls.at(-1)?.[0] as string;
      expect(lastCall).toContain("section=prepared");
    });
  });

  it("calls the search API after debounce when a query is typed", async () => {
    // Route spans and search calls to their respective fixture shapes
    mockApi.get.mockImplementation((url: string) => {
      if (url.includes("/search?")) {
        return Promise.resolve({ query: "services", results: [] });
      }
      return Promise.resolve(spansResponse);
    });
    render(<TranscriptBrowser ticker="AAPL" call={callDetail} />);
    // Wait for initial load to complete before typing
    await waitFor(() => {
      expect(screen.getByText("We are pleased to report record services revenue.")).toBeInTheDocument();
    });
    const searchInput = screen.getByPlaceholderText(/search by meaning/i);
    await userEvent.type(searchInput, "services");
    // Debounce is 400ms — waitFor polls until the search URL appears
    await waitFor(
      () => {
        const calls = (mockApi.get.mock.calls as [string][]).map(([url]) => url);
        expect(calls.some((url) => url.includes("/search?q=services"))).toBe(true);
      },
      { timeout: 1500 }
    );
  });
});
