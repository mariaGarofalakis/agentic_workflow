const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

function waitForBrowserPaint(): Promise<void> {
  return new Promise((resolve) => {
    requestAnimationFrame(() => resolve());
  });
}

export async function streamMessage(
  conversationId: string,
  message: string,
  onChunk: (chunk: string) => void,
  onReasoning: (chunk: string) => void,
  onDone: () => void,
  onError: (message: string) => void
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      conversation_id: conversationId,
      message,
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error("Streaming request failed");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finished = false;

  while (true) {
    const { value, done } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const event of events) {
      const line = event
        .split("\n")
        .find((line) => line.startsWith("data: "));

      if (!line) continue;

      let payload: {
        type: string;
        content?: string;
        message?: string;
      };

      try {
        payload = JSON.parse(line.slice(6));
        console.log(
          "SSE payload:",
          payload.type,
          performance.now(),
          payload.content
        );
      } catch {
        continue;
      }

      if (payload.type === "chunk") {
        onChunk(payload.content ?? "");
      } else if (payload.type === "reasoning") {
        onReasoning(payload.content ?? "");

        // Important:
        // Let React/browser paint the reasoning text before more events clear it.
        await waitForBrowserPaint();
      } else if (payload.type === "done") {
        finished = true;
        onDone();
        return;
      } else if (payload.type === "error") {
        finished = true;
        onError(payload.message ?? "Unknown streaming error");
        return;
      }
    }
  }

  if (!finished) {
    onDone();
  }
}