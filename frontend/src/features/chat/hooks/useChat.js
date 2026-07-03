import { useCallback, useState } from "react";

const WELCOME_MESSAGE = {
  id: "welcome",
  role: "assistant",
  content:
    "Hello! I'm the HP Support Agent. Ask me anything about HP documentation — product specs, troubleshooting, setup guides, and more.",
  createdAt: new Date().toISOString(),
};

export function useChat() {
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [sending, setSending] = useState(false);

  const sendMessage = useCallback(async (content) => {
    const trimmed = content.trim();
    if (!trimmed || sending) {
      return;
    }

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      createdAt: new Date().toISOString(),
    };

    setMessages((current) => [...current, userMessage]);
    setSending(true);

    await new Promise((resolve) => setTimeout(resolve, 600));

    const assistantMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content:
        "The chat API is not connected yet. Your message was received — RAG-powered responses will appear here once the backend is ready.",
      createdAt: new Date().toISOString(),
    };

    setMessages((current) => [...current, assistantMessage]);
    setSending(false);
  }, [sending]);

  return { messages, sending, sendMessage };
}
