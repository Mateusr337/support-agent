import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../../../services/api.js";
import { chatService, PAGE_SIZE } from "../../../services/chatService.js";

const WELCOME_MESSAGE = {
  id: "welcome",
  role: "assistant",
  content:
    "Hello! I'm the HP Support Agent. Ask me anything about HP documentation — product specs, troubleshooting, setup guides, and more.",
  createdAt: new Date().toISOString(),
};

export function useChat() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [hasMoreOlder, setHasMoreOlder] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function initSession() {
      setLoading(true);
      setError("");

      try {
        const session = await chatService.getOrCreateActiveSession();
        const page = await chatService.getSessionMessages(session.id, { limit: PAGE_SIZE });

        if (cancelled) {
          return;
        }

        setSessionId(session.id);
        setHasMoreOlder(page.has_more);
        setMessages(
          page.items.length === 0
            ? [WELCOME_MESSAGE]
            : chatService.mapMessages(page.items)
        );
      } catch (err) {
        if (!cancelled) {
          setMessages([]);
          setError(
            err instanceof ApiError
              ? err.message
              : "Unable to start chat session. Please try again."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    initSession();

    return () => {
      cancelled = true;
    };
  }, []);

  const loadOlderMessages = useCallback(async () => {
    if (!sessionId || loadingOlder || !hasMoreOlder) {
      return;
    }

    const oldestLoadedId = messages.find((message) => message.id !== WELCOME_MESSAGE.id)?.id;
    if (!oldestLoadedId || oldestLoadedId === WELCOME_MESSAGE.id) {
      return;
    }

    setLoadingOlder(true);
    setError("");

    try {
      const page = await chatService.getSessionMessages(sessionId, {
        limit: PAGE_SIZE,
        offset: Number(oldestLoadedId),
      });

      setHasMoreOlder(page.has_more);
      if (page.items.length > 0) {
        setMessages((current) => [...chatService.mapMessages(page.items), ...current]);
      }
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to load older messages. Please try again."
      );
    } finally {
      setLoadingOlder(false);
    }
  }, [sessionId, loadingOlder, hasMoreOlder, messages]);

  const sendMessage = useCallback(
    async (content) => {
      const trimmed = content.trim();
      if (!trimmed || sending || !sessionId) {
        return;
      }

      const optimisticId = crypto.randomUUID();
      const userMessage = {
        id: optimisticId,
        role: "user",
        content: trimmed,
        createdAt: new Date().toISOString(),
      };

      setMessages((current) => {
        const withoutWelcome =
          current.length === 1 && current[0].id === WELCOME_MESSAGE.id ? [] : current;
        return [...withoutWelcome, userMessage];
      });
      setSending(true);
      setError("");

      try {
        const result = await chatService.sendMessage(sessionId, trimmed);
        setMessages((current) => {
          const withoutOptimistic = current.filter((message) => message.id !== optimisticId);
          return [...withoutOptimistic, result.user_message, result.assistant_message];
        });
      } catch (err) {
        setMessages((current) => current.filter((message) => message.id !== optimisticId));
        setError(
          err instanceof ApiError
            ? err.message
            : "Unable to send message. Please try again."
        );
      } finally {
        setSending(false);
      }
    },
    [sessionId, sending]
  );

  return {
    messages,
    loading,
    loadingOlder,
    hasMoreOlder,
    sending,
    error,
    sendMessage,
    loadOlderMessages,
    canSend: Boolean(sessionId),
  };
}
