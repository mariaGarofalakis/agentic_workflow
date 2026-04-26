import { useChat } from "./hooks/useChat";
import { MessageList } from "./components/MessageList";
import { ChatInput } from "./components/ChatInput";

export default function App() {
  const { messages, isLoading, reasoningText, sendMessage } = useChat();

  return (
    <div className="app-shell">
      <div className="chat-card">
        <header className="chat-header">Minimal Agent Chatbot</header>

        <MessageList messages={messages} />

        {reasoningText && (
          <div className="reasoning-box">
            {reasoningText}
          </div>
        )}

        <ChatInput onSend={sendMessage} disabled={isLoading} />
      </div>
    </div>
  );
}