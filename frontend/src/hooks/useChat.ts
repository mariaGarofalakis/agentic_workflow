import { useRef, useState } from "react";
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
  const [reasoningText, setReasoningText] = useState("");

  const hasStartedAnswerRef = useRef(false);
  const clearReasoningTimerRef = useRef<number | null>(null);

  async function ensureConversationId(): Promise<string> {
    if (conversationId) {
      return conversationId;
    }

    const newConversationId = await createConversation("New chat");
    setConversationId(newConversationId);
    return newConversationId;
  }

  function clearReasoningSoon(delayMs: number) {
    if (clearReasoningTimerRef.current !== null) {
      window.clearTimeout(clearReasoningTimerRef.current);
    }

    clearReasoningTimerRef.current = window.setTimeout(() => {
      setReasoningText("");
      clearReasoningTimerRef.current = null;
    }, delayMs);
  }

  async function sendMessage(text: string): Promise<void> {
    if (!text.trim() || isLoading) return;

    hasStartedAnswerRef.current = false;

    if (clearReasoningTimerRef.current !== null) {
      window.clearTimeout(clearReasoningTimerRef.current);
      clearReasoningTimerRef.current = null;
    }

    setReasoningText("Thinking…");

    setMessages((prev) => [...prev, createMessage("user", text)]);

    const assistantId = crypto.randomUUID();

    setMessages((prev) => [
      ...prev,
      {
        id: assistantId,
        role: "assistant",
        content: "",
      },
    ]);

    setIsLoading(true);

    try {
      const activeConversationId = await ensureConversationId();

      await streamMessage(
        activeConversationId,
        text,

        // Normal assistant answer chunk.
        (chunk) => {
          const isRealAnswerChunk = chunk.trim().length > 0;

          if (isRealAnswerChunk && !hasStartedAnswerRef.current) {
            hasStartedAnswerRef.current = true;

            // Give the user a moment to see the reasoning before it disappears.
            clearReasoningSoon(700);
          }

          setMessages((prev) =>
            prev.map((message) => {
              if (message.id !== assistantId) {
                return message;
              }

              // Avoid showing blank assistant message from "\n" chunks.
              if (!message.content && !isRealAnswerChunk) {
                return message;
              }

              return {
                ...message,
                content: message.content + chunk,
              };
            })
          );
        },

        // Reasoning/debug chunk.
        (reasoningChunk) => {
          if (!reasoningChunk.trim()) return;

          // Once the real answer has started, ignore late reasoning.
          if (hasStartedAnswerRef.current) return;

          setReasoningText((prev) => {
            if (prev === "Thinking…") {
              return reasoningChunk;
            }

            return prev + reasoningChunk;
          });
        },

        // Done.
        () => {
          setIsLoading(false);
          clearReasoningSoon(300);
        },

        // Error.
        (errorMessage) => {
          setMessages((prev) =>
            prev.map((message) =>
              message.id === assistantId
                ? {
                    ...message,
                    content: `Error: ${errorMessage}`,
                  }
                : message
            )
          );

          setIsLoading(false);
          setReasoningText("");
        }
      );
    } catch {
      setMessages((prev) =>
        prev.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                content: "Error: failed to stream response.",
              }
            : message
        )
      );

      setIsLoading(false);
      setReasoningText("");
    }
  }

  return {
    messages,
    isLoading,
    reasoningText,
    sendMessage,
  };
}