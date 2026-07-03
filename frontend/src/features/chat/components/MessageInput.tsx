import { useState, type FormEvent, type KeyboardEvent } from "react";
import Button from "../../../components/ui/Button";
import "./MessageInput.css";

interface MessageInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export default function MessageInput({ onSend, disabled = false }: MessageInputProps) {
  const [value, setValue] = useState("");

  function submitMessage() {
    if (!value.trim() || disabled) {
      return;
    }

    onSend(value);
    setValue("");
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitMessage();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submitMessage();
    }
  }

  return (
    <form className="message-input-form" onSubmit={handleSubmit}>
      <textarea
        className="message-input"
        placeholder="Ask about HP products, setup, or troubleshooting..."
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        rows={1}
        disabled={disabled}
        aria-label="Message"
      />
      <Button type="submit" disabled={disabled || !value.trim()} aria-label="Send message">
        Send
      </Button>
    </form>
  );
}
