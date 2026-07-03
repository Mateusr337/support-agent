import Spinner from "../../../components/ui/Spinner.jsx";
import ChatHeader from "./ChatHeader.jsx";
import MessageInput from "./MessageInput.jsx";
import MessageList from "./MessageList.jsx";
import { useChat } from "../hooks/useChat.js";
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
    canSend,
  } = useChat();

  if (loading) {
    return (
      <div className="chat-window">
        <ChatHeader />
        <Spinner fullPage label="Starting chat session..." />
      </div>
    );
  }

  return (
    <div className="chat-window">
      <ChatHeader />
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
