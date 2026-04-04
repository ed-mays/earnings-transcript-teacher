import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { MetadataPanel } from "@/components/transcript/MetadataPanel";
import { callDetail } from "../../utils/fixtures";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

// api.post is called fire-and-forget for section tracking — mock to keep tests clean
vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn().mockResolvedValue({}),
    post: vi.fn().mockResolvedValue({ ok: true }),
  },
}));

describe("MetadataPanel", () => {
  it("has all sections collapsed by default", () => {
    render(<MetadataPanel call={callDetail} />);
    // No section content should be visible before any clicks
    expect(screen.queryByText("Overall sentiment")).not.toBeInTheDocument();
    expect(screen.queryByText("Executive tone")).not.toBeInTheDocument();
  });

  it("expands a collapsed section when its header is clicked", async () => {
    render(<MetadataPanel call={callDetail} />);
    await userEvent.click(screen.getByText("Read the Room"));
    // Now executive tone label should appear
    expect(screen.getByText(/executive tone/i)).toBeInTheDocument();
  });

  it("collapses an expanded section when its header is clicked again", async () => {
    render(<MetadataPanel call={callDetail} />);
    // Orient starts collapsed — click to expand then click to collapse
    await userEvent.click(screen.getByText("Orient"));
    expect(screen.getByText("Overall sentiment")).toBeInTheDocument();
    await userEvent.click(screen.getByText("Orient"));
    expect(screen.queryByText("Overall sentiment")).not.toBeInTheDocument();
  });

  it("shows Orient content after expanding", async () => {
    render(<MetadataPanel call={callDetail} />);
    await userEvent.click(screen.getByText("Orient"));
    expect(screen.getByText("positive")).toBeInTheDocument();
  });
});
