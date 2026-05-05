import { useRef, useState } from "react";
import { streamMessage, UiHint } from "../api/chat";
import { createConversation } from "../api/conversations";
import { getTravelPreferences } from "../api/travelPreferences";
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
  const [userId, setUserId] = useState<string | null>(null);
  const [reasoningText, setReasoningText] = useState("");
  const [uiHint, setUiHint] = useState<UiHint | null>(null);

  const [preferencesLoaded, setPreferencesLoaded] = useState(false);
  const [preferencesMissing, setPreferencesMissing] = useState(false);

  const hasStartedAnswerRef = useRef(false);
  const clearReasoningTimerRef = useRef<number | null>(null);

  function openPreferences() {
    setPreferencesMissing(true);
  }

  async function ensureConversationId(): Promise<string> {
    if (conversationId) return conversationId;

    const result = await createConversation("New chat");

    setConversationId(result.conversation_id);
    setUserId(result.user_id);

    if (result.user_id) {
      try {
        const preferences = await getTravelPreferences(result.user_id);
        setPreferencesMissing(preferences === null);
      } catch {
        setPreferencesMissing(true);
      } finally {
        setPreferencesLoaded(true);
      }
    } else {
      setPreferencesMissing(true);
      setPreferencesLoaded(true);
    }

    return result.conversation_id;
  }

  function handlePreferencesSaved() {
    setPreferencesMissing(false);
    setPreferencesLoaded(true);
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

    const activeConversationId = await ensureConversationId();

    if (!preferencesLoaded || preferencesMissing) {
      return;
    }

    hasStartedAnswerRef.current = false;
    setUiHint(null);

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
      await streamMessage(
        activeConversationId,
        text,
        (chunk) => {
          const isRealAnswerChunk = chunk.trim().length > 0;

          if (isRealAnswerChunk && !hasStartedAnswerRef.current) {
            hasStartedAnswerRef.current = true;
            clearReasoningSoon(700);
          }

          setMessages((prev) =>
            prev.map((message) => {
              if (message.id !== assistantId) return message;

              if (!message.content && !isRealAnswerChunk) return message;

              return {
                ...message,
                content: message.content + chunk,
              };
            })
          );
        },
        (reasoningChunk) => {
          if (!reasoningChunk.trim()) return;
          if (hasStartedAnswerRef.current) return;

          setReasoningText((prev) =>
            prev === "Thinking…" ? reasoningChunk : prev + reasoningChunk
          );
        },
        (hint) => {
          setUiHint(hint);
        },
        () => {
          setIsLoading(false);
          clearReasoningSoon(300);
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
          setReasoningText("");
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
      setReasoningText("");
    }
  }

  return {
    messages,
    isLoading,
    reasoningText,
    sendMessage,
    uiHint,
    userId,
    preferencesMissing,
    handlePreferencesSaved,
    openPreferences,
  };
}