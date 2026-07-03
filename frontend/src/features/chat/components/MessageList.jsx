import { useEffect, useRef } from "react";
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

export default function MessageList({ messages, sending }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  return (
    <div className="message-list" role="log" aria-live="polite" aria-relevant="additions">
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
