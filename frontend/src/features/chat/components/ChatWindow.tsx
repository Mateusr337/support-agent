import Spinner from "../../../components/ui/Spinner";
import AppHeader from "../../../components/layout/AppHeader";
import MessageInput from "./MessageInput";
import MessageList from "./MessageList";
import { useChat } from "../hooks/useChat";
import "./ChatWindow.css";

export default function ChatWindow() {
  const {
    messages,
    loading,
    loadingOlder,
    hasMoreOlder,
    sending,
    error,
    sendMessage,
    loadOlderMessages,
    reloadSession,
    canSend,
  } = useChat();

  if (loading) {
    return (
      <div className="chat-window">
        <AppHeader />
        <Spinner fullPage label="Starting chat session..." />
      </div>
    );
  }

  return (
    <div className="chat-window">
      <AppHeader onReload={reloadSession} />
      {error && (
        <div className="chat-error" role="alert">
          {error}
        </div>
      )}
      <MessageList
        messages={messages}
        sending={sending}
        loadingOlder={loadingOlder}
        hasMoreOlder={hasMoreOlder}
        onLoadOlder={loadOlderMessages}
      />
      <MessageInput onSend={sendMessage} disabled={sending || !canSend} />
    </div>
  );
}
