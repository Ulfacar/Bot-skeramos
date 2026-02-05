import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getConversations } from "../services/api";

const STATUS_LABELS = {
  in_progress: "В процессе",
  bot_completed: "Бот справился",
  needs_operator: "Нужен менеджер",
  operator_active: "Менеджер отвечает",
  closed: "Закрыт",
};

const STATUS_COLORS = {
  in_progress: "#3b82f6",
  bot_completed: "#22c55e",
  needs_operator: "#ef4444",
  operator_active: "#f59e0b",
  closed: "#6b7280",
};

const CATEGORY_LABELS = {
  master_class: "Мастер-класс",
  hotel: "Отель",
  custom_order: "Инд. заказ",
  general: "Общий",
};

const FILTERS = [
  { value: "", label: "Все" },
  { value: "needs_operator", label: "Нужен менеджер" },
  { value: "in_progress", label: "В процессе" },
  { value: "bot_completed", label: "Бот справился" },
  { value: "operator_active", label: "Менеджер отвечает" },
  { value: "closed", label: "Закрытые" },
];

export default function ConversationsPage() {
  const [conversations, setConversations] = useState([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const res = await getConversations(filter || undefined);
      setConversations(res.data);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
    // Обновляем каждые 10 секунд
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, [filter]);

  return (
    <div className="conversations-page">
      <div className="page-header">
        <h2>Диалоги</h2>
        <button className="btn-refresh" onClick={load}>
          Обновить
        </button>
      </div>

      <div className="filters">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            className={`filter-btn ${filter === f.value ? "active" : ""}`}
            onClick={() => setFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading && conversations.length === 0 ? (
        <p className="loading">Загрузка...</p>
      ) : conversations.length === 0 ? (
        <p className="empty">Диалогов пока нет</p>
      ) : (
        <div className="conversation-list">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className="conversation-card"
              onClick={() => navigate(`/chat/${conv.id}`)}
            >
              <div className="conv-top">
                <span className="conv-client">
                  {conv.client?.name || conv.client?.username || `Клиент #${conv.client_id}`}
                </span>
                <span
                  className="conv-status"
                  style={{ background: STATUS_COLORS[conv.status] }}
                >
                  {STATUS_LABELS[conv.status]}
                </span>
              </div>
              <div className="conv-bottom">
                <span className="conv-category">
                  {CATEGORY_LABELS[conv.category]}
                </span>
                <span className="conv-channel">
                  {conv.client?.channel === "telegram" ? "Telegram" : "WhatsApp"}
                </span>
                <span className="conv-date">
                  {new Date(conv.updated_at).toLocaleString("ru-RU")}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
