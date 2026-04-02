import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ChatInput } from "@/components/chat/ChatInput";

describe("ChatInput", () => {
  it("calls onSend with trimmed text and clears the textarea on Enter", async () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} isStreaming={false} />);
    const textarea = screen.getByRole("textbox");
    await userEvent.type(textarea, "  What is services revenue?  ");
    await userEvent.keyboard("{Enter}");
    expect(onSend).toHaveBeenCalledWith("What is services revenue?");
    expect(textarea).toHaveValue("");
  });

  it("does not submit on Shift+Enter — inserts a newline instead", async () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} isStreaming={false} />);
    const textarea = screen.getByRole("textbox");
    await userEvent.type(textarea, "Line one");
    await userEvent.keyboard("{Shift>}{Enter}{/Shift}");
    expect(onSend).not.toHaveBeenCalled();
    expect(textarea).toHaveValue("Line one\n");
  });

  it("shows an enabled Stop button and disabled textarea when isStreaming is true", () => {
    render(<ChatInput onSend={vi.fn()} isStreaming={true} />);
    expect(screen.getByRole("textbox")).toBeDisabled();
    const stopButton = screen.getByRole("button", { name: /stop/i });
    expect(stopButton).toBeInTheDocument();
    expect(stopButton).not.toBeDisabled();
  });

  it("calls onAbort when the Stop button is clicked during streaming", async () => {
    const onAbort = vi.fn();
    render(<ChatInput onSend={vi.fn()} onAbort={onAbort} isStreaming={true} />);
    await userEvent.click(screen.getByRole("button", { name: /stop/i }));
    expect(onAbort).toHaveBeenCalledTimes(1);
  });

  it("does not call onSend when input is blank", async () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} isStreaming={false} />);
    await userEvent.keyboard("{Enter}");
    expect(onSend).not.toHaveBeenCalled();
  });
});
