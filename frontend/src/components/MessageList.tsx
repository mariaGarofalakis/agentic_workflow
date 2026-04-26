import type { Message } from "../types/chat";

type Props = {
  messages: Message[];
};

export function MessageList({ messages }: Props) {
  const visibleMessages = messages.filter((message) => {
    if (message.role === "user") return true;
    return message.content.trim().length > 0;
  });

  return (
    <div className="messages">
      {visibleMessages.map((message) => (
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