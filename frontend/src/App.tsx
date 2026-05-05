import { useChat } from "./hooks/useChat";
import { MessageList } from "./components/MessageList";
import { ChatInput } from "./components/ChatInput";
import { TravelPreferencesCard } from "./components/TravelPreferencesCard";

export default function App() {
  const {
    messages,
    isLoading,
    reasoningText,
    sendMessage,
    uiHint,
    userId,
    preferencesMissing,
    handlePreferencesSaved,
    openPreferences,
  } = useChat();

  return (
    <div className="app-shell">
      <div className="chat-card">
        <header className="chat-header">
          <span>Minimal Agent Chatbot</span>

          {userId && (
            <button
              type="button"
              className="header-button"
              onClick={openPreferences}
            >
              Preferences
            </button>
          )}
        </header>

        <MessageList messages={messages} />

        {uiHint?.component === "travel_preferences_card" && (
          <div className="preferences-card">
            <strong>More trip details needed</strong>
            <p>Missing: {uiHint.missing_fields.join(", ")}</p>
          </div>
        )}

        {reasoningText && <div className="reasoning-box">{reasoningText}</div>}

        <ChatInput onSend={sendMessage} disabled={isLoading} />
      </div>

      {preferencesMissing && userId && (
        <TravelPreferencesCard
          userId={userId}
          onSaved={handlePreferencesSaved}
        />
      )}
    </div>
  );
}