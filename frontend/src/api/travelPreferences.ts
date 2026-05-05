const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export type TravelPreferences = {
  user_id: string;
  home_city: string | null;
  home_airport: string | null;
  budget_style: string | null;
  pace: "relaxed" | "balanced" | "packed" | null;
  dietary_needs: string[];
};

export type TravelPreferencesPayload = Omit<TravelPreferences, "user_id">;

async function handleError(response: Response) {
  let errorMessage = "Request failed";

  try {
    const data = await response.json();

    if (data?.detail?.message) {
      errorMessage = data.detail.message;
    } else if (data?.detail) {
      errorMessage = data.detail;
    } else {
      errorMessage = JSON.stringify(data);
    }
  } catch {
    errorMessage = await response.text();
  }

  throw new Error(errorMessage);
}

export async function getTravelPreferences(
  userId: string
): Promise<TravelPreferences | null> {
  const response = await fetch(`${API_BASE_URL}/travel-preferences/${userId}`);

  if (!response.ok) {
    await handleError(response);
  }

  return response.json();
}

export async function saveTravelPreferences(
  userId: string,
  payload: TravelPreferencesPayload
): Promise<TravelPreferences> {
  const response = await fetch(`${API_BASE_URL}/travel-preferences/${userId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    await handleError(response);
  }

  return response.json();
}