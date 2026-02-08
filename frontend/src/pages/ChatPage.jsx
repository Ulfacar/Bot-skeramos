import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  getConversation,
  getMessages,
  sendMessage,
  updateConversation,
} from "../services/api";

const STATUS_LABELS = {
  in_progress: "В процессе",
  bot_completed: "Бот справился",
  needs_operator: "Нужен менеджер",
  operator_active: "Менеджер отвечает",
  closed: "Закрыт",
};

const SENDER_LABELS = {
  client: "Клиент",
  bot: "Бот",
  operator: "Менеджер",
};

export default function ChatPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const messagesEnd = useRef(null);

  const loadData = async () => {
    try {
      const [convRes, msgRes] = await Promise.all([
        getConversation(id),
        getMessages(id),
      ]);
      setConversation(convRes.data);
      setMessages(msgRes.data);
    } catch {
      navigate("/");
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [id]);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!text.trim() || sending) return;
    setSending(true);
    try {
      await sendMessage(id, text.trim());
      setText("");
      await loadData();
    } catch (err) {
      console.error(err);
    }
    setSending(false);
  };

  const handleClose = async () => {
    await updateConversation(id, { status: "closed" });
    await loadData();
  };

  const handleTakeover = async () => {
    await updateConversation(id, { status: "operator_active" });
    await loadData();
  };

  const handleReturnToBot = async () => {
    await updateConversation(id, { status: "in_progress" });
    await loadData();
  };

  if (!conversation) return <p className="loading">Загрузка...</p>;

  const client = conversation.client;

  return (
    <div className="chat-page">
      <div className="chat-header">
        <button className="btn-back" onClick={() => navigate("/")}>
          ← Назад
        </button>
        <div className="chat-info">
          <span className="chat-client-name">
            {client?.channel === "whatsapp" ? "📱" : "✈️"}{" "}
            {client?.name || client?.username || `Клиент #${conversation.client_id}`}
          </span>
          <span className="chat-status">
            {STATUS_LABELS[conversation.status]}
          </span>
        </div>
        <div className="chat-actions">
          {conversation.status !== "closed" &&
            conversation.status !== "operator_active" && (
              <button className="btn-takeover" onClick={handleTakeover}>
                Перехватить чат
              </button>
            )}
          {conversation.status === "operator_active" && (
            <button className="btn-return-bot" onClick={handleReturnToBot}>
              Вернуть боту
            </button>
          )}
          {conversation.status !== "closed" && (
            <button className="btn-close-conv" onClick={handleClose}>
              Закрыть диалог
            </button>
          )}
        </div>
      </div>

      <div className="messages-container">
        {messages.map((msg) => (
          <div key={msg.id} className={`message message-${msg.sender}`}>
            <div className="message-sender">
              {SENDER_LABELS[msg.sender]}
            </div>
            <div className="message-text">{msg.text}</div>
            <div className="message-time">
              {new Date(msg.created_at).toLocaleString("ru-RU")}
            </div>
          </div>
        ))}
        <div ref={messagesEnd} />
      </div>

      {conversation.status !== "closed" && (
        <form className="message-form" onSubmit={handleSend}>
          <input
            type="text"
            placeholder="Написать клиенту..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={sending}
          />
          <button type="submit" disabled={sending || !text.trim()}>
            Отправить
          </button>
        </form>
      )}
    </div>
  );
}
