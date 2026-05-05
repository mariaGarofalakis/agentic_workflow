import { useState } from "react";
import { saveTravelPreferences } from "../api/travelPreferences";

type Props = {
  userId: string;
  onSaved: () => void;
};

export function TravelPreferencesCard({ userId, onSaved }: Props) {
  const [homeCity, setHomeCity] = useState("");
  const [homeAirport, setHomeAirport] = useState("");
  const [budgetStyle, setBudgetStyle] = useState("");
  const [pace, setPace] = useState<"relaxed" | "balanced" | "packed" | "">("");
  const [dietaryNeeds, setDietaryNeeds] = useState("");

  const [isSaving, setIsSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");

  function csvToList(value: string): string[] {
    return value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  async function handleSave() {
    setIsSaving(true);
    setStatusMessage("");

    // 🔍 DEBUG: see exactly what you're sending
    console.log("Saving preferences:", {
      userId,
      homeCity,
      homeAirport,
      budgetStyle,
      pace,
      dietaryNeeds,
    });

    try {
      await saveTravelPreferences(userId, {
        home_city: homeCity || null,
        home_airport: homeAirport || null,
        budget_style: budgetStyle || null,
        pace: pace || null,
        dietary_needs: csvToList(dietaryNeeds),
      });

      setStatusMessage("✅ Preferences saved.");
      onSaved();
    } catch (error) {
      console.error("Save preferences error:", error);

      setStatusMessage(
        error instanceof Error
          ? `❌ ${error.message}`
          : "❌ Could not save preferences."
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="preferences-overlay">
      <div className="preferences-modal">
        <h2>Travel preferences</h2>

        <p>
          These details will be saved and used to improve your trip planning.
          You can change them anytime later.
        </p>

        <div className="preferences-form">
          <input
            value={homeCity}
            onChange={(event) => setHomeCity(event.target.value)}
            placeholder="Home city (e.g. Copenhagen)"
          />

          <input
            value={homeAirport}
            onChange={(event) => setHomeAirport(event.target.value)}
            placeholder="Home airport (e.g. CPH)"
          />

          <input
            value={budgetStyle}
            onChange={(event) => setBudgetStyle(event.target.value)}
            placeholder="Budget style (budget, mid-range, luxury)"
          />

          <select
            value={pace}
            onChange={(event) =>
              setPace(
                event.target.value as
                  | "relaxed"
                  | "balanced"
                  | "packed"
                  | ""
              )
            }
          >
            <option value="">Preferred trip pace</option>
            <option value="relaxed">Relaxed</option>
            <option value="balanced">Balanced</option>
            <option value="packed">Packed</option>
          </select>

          <input
            value={dietaryNeeds}
            onChange={(event) => setDietaryNeeds(event.target.value)}
            placeholder="Dietary needs (comma separated)"
          />
        </div>

        <button type="button" onClick={handleSave} disabled={isSaving}>
          {isSaving ? "Saving..." : "Save preferences"}
        </button>

        {statusMessage && (
          <p style={{ marginTop: "10px", fontSize: "14px" }}>
            {statusMessage}
          </p>
        )}
      </div>
    </div>
  );
}