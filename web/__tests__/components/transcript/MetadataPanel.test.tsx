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

describe("MetadataPanel", () => {
  it("has Orient expanded and other sections collapsed by default", () => {
    render(<MetadataPanel call={callDetail} />);
    // Orient content should be visible (synthesis.overall_sentiment = "positive")
    expect(screen.getByText("positive")).toBeInTheDocument();
    // "Read the Room" content should not be visible
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
    // Orient is expanded by default — click to collapse
    await userEvent.click(screen.getByText("Orient"));
    expect(screen.queryByText("Overall sentiment")).not.toBeInTheDocument();
  });

  it("renders overall_sentiment from synthesis in the Orient section", () => {
    render(<MetadataPanel call={callDetail} />);
    expect(screen.getByText("positive")).toBeInTheDocument();
  });
});
