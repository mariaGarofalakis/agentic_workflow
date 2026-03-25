import type { Message } from "../types/chat";

type Props = {
  messages: Message[];
};

export function MessageList({ messages }: Props) {
  return (
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
  );
}