import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { ChatMessage, StreamingState } from "../../../types/chat";
import MarkdownContent from "../../../components/ui/MarkdownContent";
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
        {isUser ? <p>{message.content}</p> : <MarkdownContent content={message.content} />}
      </div>
    </div>
  );
}

function toolStatusLabel(toolName: string): string {
  if (toolName === "search_documents") {
    return "Searching HP manuals";
  }
  return `Running ${toolName.replace(/_/g, " ")}`;
}

type StreamingPhase = "thinking" | "searching" | "writing";

function getStreamingPhase(streaming: StreamingState): StreamingPhase {
  if (streaming.content.length > 0) {
    return "writing";
  }
  if (streaming.tool !== null) {
    return "searching";
  }
  return "thinking";
}

function streamingStatusLabel(phase: StreamingPhase, toolName: string | null): string {
  if (phase === "thinking") {
    return "Thinking";
  }
  if (phase === "searching" && toolName) {
    return toolStatusLabel(toolName);
  }
  return "Preparing response";
}

interface StreamingBubbleProps {
  streaming: StreamingState;
}

function StreamingSkeleton() {
  return (
    <div className="stream-skeleton" aria-hidden="true">
      <span className="stream-skeleton-line stream-skeleton-line-long" />
      <span className="stream-skeleton-line stream-skeleton-line-medium" />
    </div>
  );
}

function StreamingBubble({ streaming }: StreamingBubbleProps) {
  const phase = getStreamingPhase(streaming);
  const isWriting = phase === "writing";
  const statusLabel = streamingStatusLabel(phase, streaming.tool);

  return (
    <div className="message-row message-row-bot message-row-streaming">
      <div className="message-avatar message-avatar-active" aria-hidden="true">
        HP
      </div>
      <div className={`message-bubble message-bubble-bot message-bubble-streaming${isWriting ? "" : " message-bubble-streaming-compact"}`}>
        {!isWriting && (
          <>
            <div className="stream-status" role="status" aria-live="polite">
              <span className="stream-status-indicator" aria-hidden="true">
                <span className="stream-status-dot" />
                <span className="stream-status-dot" />
                <span className="stream-status-dot" />
              </span>
              <span className="stream-status-label">{statusLabel}</span>
            </div>
            <StreamingSkeleton />
          </>
        )}
        {isWriting && (
          <div className="stream-content" aria-live="polite" aria-busy="true">
            <MarkdownContent content={streaming.content} showCursor />
          </div>
        )}
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
  streaming: StreamingState | null;
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
  streaming,
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

    if ((appendedAtBottom || sending || streaming) && !loadingOlder) {
      scrollToBottom(list);
    }
  }, [messages, sending, streaming, loadingOlder]);

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

      {streaming && <StreamingBubble streaming={streaming} />}
    </div>
  );
}
