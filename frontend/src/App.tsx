import { useState } from "react";
import { streamMessage } from "./api/chat";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

function createMessage(role: Message["role"], content: string): Message {
  return {
    id: crypto.randomUUID(),
    role,
    content,
  };
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([
    createMessage("assistant", "Hi — ask me anything."),
  ]);
  const [value, setValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();

    const trimmed = value.trim();
    if (!trimmed || isLoading) return;

    setValue("");
    setMessages((prev) => [...prev, createMessage("user", trimmed)]);

    const assistantId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: "assistant", content: "" },
    ]);

    setIsLoading(true);

    try {
      await streamMessage(
        trimmed,
        (chunk) => {
          setMessages((prev) =>
            prev.map((message) =>
              message.id === assistantId
                ? { ...message, content: message.content + chunk }
                : message
            )
          );
        },
        () => {
          setIsLoading(false);
        },
        (errorMessage) => {
          setMessages((prev) =>
            prev.map((message) =>
              message.id === assistantId
                ? { ...message, content: `Error: ${errorMessage}` }
                : message
            )
          );
          setIsLoading(false);
        }
      );
    } catch (error) {
      setMessages((prev) =>
        prev.map((message) =>
          message.id === assistantId
            ? { ...message, content: "Error: failed to stream response." }
            : message
        )
      );
      setIsLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <div className="chat-card">
        <header className="chat-header">Minimal Agent Chatbot</header>

        <div className="messages">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`message ${message.role === "user" ? "user" : "assistant"}`}
            >
              <div className="message-role">
                {message.role === "user" ? "You" : "Assistant"}
              </div>
              <div>{message.content}</div>
            </div>
          ))}
        </div>

        <form className="chat-input" onSubmit={handleSubmit}>
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Type your message..."
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}