import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ChatThread } from "@/components/chat/ChatThread";
import type { ChatMessage } from "@/lib/chat";

const noMessages: ChatMessage[] = [];
const messages: ChatMessage[] = [
  { role: "user", content: "What drove revenue growth?" },
  { role: "assistant", content: "Services revenue was the primary driver." },
];

describe("ChatThread", () => {
  it("shows empty state prompt when there are no messages and no streaming", () => {
    render(
      <ChatThread messages={noMessages} streamingContent="" />
    );
    expect(
      screen.getByText(/ask a question about this earnings call/i)
    ).toBeInTheDocument();
  });

  it("shows loading indicator when loadingSuggestions is true", () => {
    render(
      <ChatThread
        messages={noMessages}
        streamingContent=""
        loadingSuggestions={true}
      />
    );
    expect(screen.getByText(/loading suggested starter questions/i)).toBeInTheDocument();
  });

  it("shows suggestion buttons when suggestions are provided", () => {
    render(
      <ChatThread
        messages={noMessages}
        streamingContent=""
        suggestions={["Tell me about services", "What is the evasion level?"]}
        loadingSuggestions={false}
      />
    );
    expect(screen.getByText("Tell me about services")).toBeInTheDocument();
    expect(screen.getByText("What is the evasion level?")).toBeInTheDocument();
  });

  it("calls onSuggestionClick with the suggestion text when clicked", async () => {
    const onSuggestionClick = vi.fn();
    render(
      <ChatThread
        messages={noMessages}
        streamingContent=""
        suggestions={["Tell me about services"]}
        loadingSuggestions={false}
        onSuggestionClick={onSuggestionClick}
      />
    );
    await userEvent.click(screen.getByText("Tell me about services"));
    expect(onSuggestionClick).toHaveBeenCalledWith("Tell me about services");
  });

  it("renders user and assistant message bubbles", () => {
    render(<ChatThread messages={messages} streamingContent="" />);
    expect(screen.getByText("What drove revenue growth?")).toBeInTheDocument();
    expect(
      screen.getByText("Services revenue was the primary driver.")
    ).toBeInTheDocument();
  });

  it("renders streaming content with a cursor indicator", () => {
    render(
      <ChatThread
        messages={noMessages}
        streamingContent="Streaming response in progress"
      />
    );
    expect(screen.getByText("Streaming response in progress")).toBeInTheDocument();
    // Streaming cursor is a span with animate-pulse inside the bubble
    expect(document.querySelector(".animate-pulse")).toBeInTheDocument();
  });
});
