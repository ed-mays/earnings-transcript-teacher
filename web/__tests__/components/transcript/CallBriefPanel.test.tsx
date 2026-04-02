import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { CallBriefPanel } from "@/components/transcript/CallBriefPanel";
import {
  callBrief,
  takeaways,
  misconceptions,
  signalStrip,
} from "../../utils/fixtures";

describe("CallBriefPanel", () => {
  it("renders the context_line", () => {
    render(
      <CallBriefPanel
        brief={callBrief}
        takeaways={takeaways}
        misconceptions={[]}
        signal_strip={null}
      />
    );
    expect(
      screen.getByText(
        "Apple reported Q4 earnings beating analyst expectations."
      )
    ).toBeInTheDocument();
  });

  it("renders signal strip badges when signal_strip is provided", () => {
    render(
      <CallBriefPanel
        brief={callBrief}
        takeaways={takeaways}
        misconceptions={[]}
        signal_strip={signalStrip}
      />
    );
    expect(screen.getByText(/optimistic/i)).toBeInTheDocument();
    expect(screen.getByText(/bullish/i)).toBeInTheDocument();
    expect(screen.getByText(/evasion: low/i)).toBeInTheDocument();
  });

  it("shows Expand all button when there are 2 or more misconceptions", () => {
    render(
      <CallBriefPanel
        brief={callBrief}
        takeaways={takeaways}
        misconceptions={misconceptions}
        signal_strip={null}
      />
    );
    expect(
      screen.getByRole("button", { name: /expand all/i })
    ).toBeInTheDocument();
  });

  it("does not show Expand all button when there is only 1 misconception", () => {
    render(
      <CallBriefPanel
        brief={callBrief}
        takeaways={takeaways}
        misconceptions={[misconceptions[0]]}
        signal_strip={null}
      />
    );
    expect(
      screen.queryByRole("button", { name: /expand all/i })
    ).not.toBeInTheDocument();
  });

  it("toggles to Collapse all after clicking Expand all", async () => {
    render(
      <CallBriefPanel
        brief={callBrief}
        takeaways={takeaways}
        misconceptions={misconceptions}
        signal_strip={null}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: /expand all/i }));
    expect(
      screen.getByRole("button", { name: /collapse all/i })
    ).toBeInTheDocument();
  });
});
