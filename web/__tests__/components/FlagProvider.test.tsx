import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { FlagProvider } from "@/components/FlagProvider";
import { useFlag } from "@/lib/useFlag";

function FlagConsumer({ flagKey, defaultValue }: { flagKey: string; defaultValue?: boolean }) {
  const value = useFlag(flagKey, defaultValue);
  return <span data-testid="value">{String(value)}</span>;
}

describe("useFlag", () => {
  it("returns true for an enabled flag", () => {
    render(
      <FlagProvider initialFlags={{ chat_enabled: true }}>
        <FlagConsumer flagKey="chat_enabled" />
      </FlagProvider>
    );
    expect(screen.getByTestId("value").textContent).toBe("true");
  });

  it("returns false for a disabled flag", () => {
    render(
      <FlagProvider initialFlags={{ chat_enabled: false }}>
        <FlagConsumer flagKey="chat_enabled" />
      </FlagProvider>
    );
    expect(screen.getByTestId("value").textContent).toBe("false");
  });

  it("returns false by default for a missing key", () => {
    render(
      <FlagProvider initialFlags={{}}>
        <FlagConsumer flagKey="nonexistent" />
      </FlagProvider>
    );
    expect(screen.getByTestId("value").textContent).toBe("false");
  });

  it("returns the explicit default for a missing key", () => {
    render(
      <FlagProvider initialFlags={{}}>
        <FlagConsumer flagKey="nonexistent" defaultValue={true} />
      </FlagProvider>
    );
    expect(screen.getByTestId("value").textContent).toBe("true");
  });

  it("flag value overrides default", () => {
    render(
      <FlagProvider initialFlags={{ chat_enabled: false }}>
        <FlagConsumer flagKey="chat_enabled" defaultValue={true} />
      </FlagProvider>
    );
    expect(screen.getByTestId("value").textContent).toBe("false");
  });
});
