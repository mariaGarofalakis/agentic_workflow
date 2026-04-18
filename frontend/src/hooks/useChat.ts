import { useState } from "react";
import { streamMessage } from "../api/chat";
import { createConversation } from "../api/conversations";
import { Message } from "../types/chat";

function createMessage(role: Message["role"], content: string): Message {
  return {
    id: crypto.randomUUID(),
    role,
    content,
  };
}

export function useChat() {
 const [messages, setMessages] = useState<Message[]>([
    createMessage("assistant", "Hi — ask me anything."),
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);

  async function ensureConversationId(): Promise<string> {
    if (conversationId) {
      return conversationId;
    }

    const newConversationId = await createConversation("New chat");
    setConversationId(newConversationId);
    return newConversationId;
 }

  async function sendMessage(text: string): Promise<void>{

    if (!text.trim() || isLoading) return;


    setMessages((prev) => [...prev, createMessage("user", text)]);

    const assistantId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: "assistant", content: "" },
    ]);

    setIsLoading(true);

    try {
      const activeConversationId = await ensureConversationId();

      await streamMessage(
        activeConversationId,
        text,
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
    } catch {
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
  return { messages, isLoading, sendMessage }
}
