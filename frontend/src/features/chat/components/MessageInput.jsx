import { useState } from "react";
import Button from "../../../components/ui/Button.jsx";
import "./MessageInput.css";

export default function MessageInput({ onSend, disabled = false }) {
  const [value, setValue] = useState("");

  function handleSubmit(event) {
    event.preventDefault();
    if (!value.trim() || disabled) {
      return;
    }

    onSend(value);
    setValue("");
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event);
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
