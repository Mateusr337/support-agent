import ChatHeader from "./ChatHeader.jsx";
import MessageInput from "./MessageInput.jsx";
import MessageList from "./MessageList.jsx";
import { useChat } from "../hooks/useChat.js";
import "./ChatWindow.css";

export default function ChatWindow() {
  const { messages, sending, sendMessage } = useChat();

  return (
    <div className="chat-window">
      <ChatHeader />
      <MessageList messages={messages} sending={sending} />
      <MessageInput onSend={sendMessage} disabled={sending} />
    </div>
  );
}
