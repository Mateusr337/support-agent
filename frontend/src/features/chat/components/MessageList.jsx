import { useEffect, useLayoutEffect, useRef } from "react";
import Spinner from "../../../components/ui/Spinner.jsx";
import "./MessageList.css";

function MessageBubble({ message }) {
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

export default function MessageList({
  messages,
  sending,
  loadingOlder = false,
  hasMoreOlder = false,
  onLoadOlder,
}) {
  const listRef = useRef(null);
  const bottomRef = useRef(null);
  const pendingScrollRestoreRef = useRef(null);
  const initialScrollDoneRef = useRef(false);
  const previousLastMessageIdRef = useRef(null);
  const wasLoadingOlderRef = useRef(false);

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

    const lastMessageId = messages.at(-1)?.id ?? null;
    const appendedAtBottom = lastMessageId !== previousLastMessageIdRef.current;
    previousLastMessageIdRef.current = lastMessageId;

    if (!initialScrollDoneRef.current && messages.length > 0) {
      list.scrollTop = list.scrollHeight;
      initialScrollDoneRef.current = true;
      return;
    }

    if ((appendedAtBottom || sending) && !loadingOlder) {
      list.scrollTop = list.scrollHeight;
    }
  }, [messages, sending, loadingOlder]);

  useEffect(() => {
    if (loadingOlder || !hasMoreOlder || !onLoadOlder) {
      return;
    }

    const list = listRef.current;
    if (!list) {
      return;
    }

    function handleScroll() {
      if (list.scrollTop > 80 || loadingOlder || pendingScrollRestoreRef.current) {
        return;
      }

      pendingScrollRestoreRef.current = {
        scrollHeight: list.scrollHeight,
        scrollTop: list.scrollTop,
      };
      onLoadOlder();
    }

    list.addEventListener("scroll", handleScroll, { passive: true });
    return () => list.removeEventListener("scroll", handleScroll);
  }, [loadingOlder, hasMoreOlder, onLoadOlder]);

  return (
    <div
      ref={listRef}
      className="message-list"
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

      <div ref={bottomRef} />
    </div>
  );
}
