import { FormEvent, useState } from "react";

type Props = {
  onSend: (message: string) => Promise<void>;
  disabled?: boolean;
};

export function ChatInput({ onSend, disabled = false }: Props) {
  const [value, setValue] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();

    const trimmed = value.trim();
    if (!trimmed || disabled) {
      return;
    }

    setValue("");
    await onSend(trimmed);
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Type your message..."
        disabled={disabled}
      />
      <button type="submit" disabled={disabled}>
        Send
      </button>
    </form>
  );
}