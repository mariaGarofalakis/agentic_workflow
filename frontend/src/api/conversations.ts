const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export type CreateConversationResponse = {
  conversation_id: string;
  title: string | null;
};

export async function createConversation(title?: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/conversations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      title: title ?? null,
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Failed to create conversation");
  }

  const data: CreateConversationResponse = await response.json();
  return data.conversation_id;
}