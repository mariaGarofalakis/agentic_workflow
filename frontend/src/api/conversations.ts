const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export type CreateConversationResponse = {
  conversation_id: string;
  user_id: string | null;
  title: string | null;
};

export async function createConversation(
  title?: string
): Promise<CreateConversationResponse> {
  const response = await fetch(`${API_BASE_URL}/conversations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      title: title ?? "New chat",
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to create conversation");
  }

  return response.json();
}