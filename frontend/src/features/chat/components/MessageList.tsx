import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { ChatMessage } from "../../../types/chat";
import Spinner from "../../../components/ui/Spinner";
import "./MessageList.css";

interface MessageBubbleProps {
  message: ChatMessage;
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`message-row ${isUser ? "message-row-user" : "message-row-bot"}`}>
      {!isUser && (
        <div className="message-avatar" aria-hidden="true">
          HP
        </div>
      )}
      <div className={`message-bubble ${isUser ? "message-bubble-user" : "message-bubble-bot"}`}>
        <p>{message.content}</p>
      </div>
    </div>
  );
}

interface ScrollRestoreState {
  scrollHeight: number;
  scrollTop: number;
}

interface MessageListProps {
  messages: ChatMessage[];
  sending: boolean;
  loadingOlder?: boolean;
  hasMoreOlder?: boolean;
  onLoadOlder?: () => void;
}

function scrollToBottom(el: HTMLElement): void {
  el.scrollTo({ top: el.scrollHeight, behavior: "instant" });
}

export default function MessageList({
  messages,
  sending,
  loadingOlder = false,
  hasMoreOlder = false,
  onLoadOlder,
}: MessageListProps) {
  const listRef = useRef<HTMLDivElement>(null);
  const pendingScrollRestoreRef = useRef<ScrollRestoreState | null>(null);
  const initialScrollDoneRef = useRef(false);
  const previousLastMessageIdRef = useRef<string | null>(null);
  const wasLoadingOlderRef = useRef(false);
  const [canLoadOlder, setCanLoadOlder] = useState(false);

  useLayoutEffect(() => {
    const list = listRef.current;
    if (!list) {
      return;
    }

    if (wasLoadingOlderRef.current && !loadingOlder && pendingScrollRestoreRef.current) {
      const pending = pendingScrollRestoreRef.current;
      list.scrollTop = list.scrollHeight - pending.scrollHeight + pending.scrollTop;
      pendingScrollRestoreRef.current = null;
      wasLoadingOlderRef.current = false;
      return;
    }

    wasLoadingOlderRef.current = loadingOlder;

    const lastMessageId =
      messages.length > 0 ? messages[messages.length - 1].id : null;
    const appendedAtBottom = lastMessageId !== previousLastMessageIdRef.current;
    previousLastMessageIdRef.current = lastMessageId;

    if (!initialScrollDoneRef.current && messages.length > 0) {
      scrollToBottom(list);
      initialScrollDoneRef.current = true;
      requestAnimationFrame(() => {
        const el = listRef.current;
        if (el) {
          scrollToBottom(el);
        }
        setCanLoadOlder(true);
      });
      return;
    }

    if ((appendedAtBottom || sending) && !loadingOlder) {
      scrollToBottom(list);
    }
  }, [messages, sending, loadingOlder]);

  useEffect(() => {
    if (!canLoadOlder || loadingOlder || !hasMoreOlder || !onLoadOlder) {
      return;
    }

    const listEl = listRef.current;
    if (!listEl) {
      return;
    }

    function handleScroll() {
      const el = listRef.current;
      if (
        !el ||
        el.scrollTop > 80 ||
        loadingOlder ||
        pendingScrollRestoreRef.current
      ) {
        return;
      }

      pendingScrollRestoreRef.current = {
        scrollHeight: el.scrollHeight,
        scrollTop: el.scrollTop,
      };
      onLoadOlder?.();
    }

    listEl.addEventListener("scroll", handleScroll, { passive: true });
    return () => listEl.removeEventListener("scroll", handleScroll);
  }, [canLoadOlder, loadingOlder, hasMoreOlder, onLoadOlder]);

  return (
    <div
      ref={listRef}
      className="message-list scrollable"
      role="log"
      aria-live="polite"
      aria-relevant="additions"
    >
      {loadingOlder && (
        <div className="message-list-loader" role="status" aria-label="Loading older messages">
          <Spinner label="Loading older messages" />
        </div>
      )}

      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {sending && (
        <div className="message-row message-row-bot">
          <div className="message-avatar" aria-hidden="true">
            HP
          </div>
          <div className="message-bubble message-bubble-bot message-typing">
            <span />
            <span />
            <span />
          </div>
        </div>
      )}
    </div>
  );
}
