import { useState } from "react";
import Spinner from "../../../components/ui/Spinner";
import ConfirmDialog from "../../../components/ui/ConfirmDialog";
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
    streaming,
    reloadingSession,
    error,
    sendMessage,
    loadOlderMessages,
    reloadSession,
    canSend,
  } = useChat();
  const [reloadConfirmOpen, setReloadConfirmOpen] = useState(false);

  async function handleReloadConfirm() {
    const success = await reloadSession();
    if (success) {
      setReloadConfirmOpen(false);
    }
  }

  function closeReloadConfirm() {
    if (!reloadingSession) {
      setReloadConfirmOpen(false);
    }
  }

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
      <AppHeader
        onReloadClick={() => setReloadConfirmOpen(true)}
        reloadDisabled={sending || reloadingSession}
      />
      <ConfirmDialog
        open={reloadConfirmOpen}
        title="Start a new chat?"
        description="This will clear your current conversation and begin a fresh session. This action cannot be undone."
        confirmLabel="Start new chat"
        cancelLabel="Keep chatting"
        confirmVariant="danger"
        loading={reloadingSession}
        onConfirm={handleReloadConfirm}
        onCancel={closeReloadConfirm}
      />
      {error && (
        <div className="chat-error" role="alert">
          {error}
        </div>
      )}
      <MessageList
        messages={messages}
        sending={sending}
        streaming={streaming}
        loadingOlder={loadingOlder}
        hasMoreOlder={hasMoreOlder}
        onLoadOlder={loadOlderMessages}
      />
      <MessageInput onSend={sendMessage} disabled={sending || !canSend} />
    </div>
  );
}
