import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LayerToggle } from "@/components/learn/LayerToggle";
import { DEFAULT_LAYERS } from "@/components/learn/types";

describe("LayerToggle", () => {
  it("renders a pill for each of the four layers", () => {
    render(<LayerToggle layers={DEFAULT_LAYERS} onChange={() => {}} />);
    expect(screen.getByRole("switch", { name: /Guidance/i })).toBeInTheDocument();
    expect(screen.getByRole("switch", { name: /Evasion/i })).toBeInTheDocument();
    expect(screen.getByRole("switch", { name: /Sentiment/i })).toBeInTheDocument();
    expect(screen.getByRole("switch", { name: /Terms/i })).toBeInTheDocument();
  });

  it("reflects active state via aria-checked", () => {
    render(
      <LayerToggle
        layers={{ guidance: true, evasion: false, sentiment: true, terms: false }}
        onChange={() => {}}
      />,
    );
    expect(screen.getByRole("switch", { name: /Guidance/i })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByRole("switch", { name: /Evasion/i })).toHaveAttribute(
      "aria-checked",
      "false",
    );
  });

  it("calls onChange with the layer key when a pill is clicked", async () => {
    const onChange = vi.fn();
    render(<LayerToggle layers={DEFAULT_LAYERS} onChange={onChange} />);
    await userEvent.click(screen.getByRole("switch", { name: /Evasion/i }));
    expect(onChange).toHaveBeenCalledWith("evasion");
  });
});
