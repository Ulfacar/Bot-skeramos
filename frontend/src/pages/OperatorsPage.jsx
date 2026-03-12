import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  getOperators,
  createOperator,
  deactivateOperator,
  activateOperator,
  getMe,
} from "../services/api";

export default function OperatorsPage() {
  const [operators, setOperators] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [error, setError] = useState("");
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    is_admin: false,
    telegram_id: "",
  });
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [opsRes, meRes] = await Promise.all([getOperators(), getMe()]);
      setOperators(opsRes.data);
      setCurrentUser(meRes.data);
    } catch (e) {
      if (e.response?.status === 403) {
        navigate("/");
      }
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async () => {
    setError("");
    if (!formData.name.trim() || !formData.email.trim() || !formData.password.trim()) {
      setError("Заполните все обязательные поля");
      return;
    }
    if (formData.password.length < 8) {
      setError("Пароль должен быть не менее 8 символов");
      return;
    }
    try {
      await createOperator({
        name: formData.name,
        email: formData.email,
        password: formData.password,
        is_admin: formData.is_admin,
        telegram_id: formData.telegram_id || null,
      });
      setShowAddModal(false);
      setFormData({ name: "", email: "", password: "", is_admin: false, telegram_id: "" });
      loadData();
    } catch (e) {
      setError(e.response?.data?.detail || "Ошибка создания");
    }
  };

  const handleToggleActive = async (op) => {
    try {
      if (op.is_active) {
        await deactivateOperator(op.id);
      } else {
        await activateOperator(op.id);
      }
      loadData();
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) return <p className="loading">Загрузка...</p>;

  return (
    <div className="operators-page">
      <div className="operators-header">
        <button className="btn-back" onClick={() => navigate("/")}>
          ← Назад
        </button>
        <h1>Менеджеры</h1>
        <button className="btn-add" onClick={() => setShowAddModal(true)}>
          + Добавить
        </button>
      </div>

      <div className="operators-list">
        {operators.length === 0 ? (
          <p className="empty">Менеджеров пока нет</p>
        ) : (
          operators.map((op) => (
            <div
              key={op.id}
              className={`operator-card ${!op.is_active ? "inactive" : ""}`}
            >
              <div className="operator-info">
                <div className="operator-name">
                  {op.name}
                  {op.is_admin && <span className="badge-admin">Админ</span>}
                  {!op.is_active && <span className="badge-inactive">Отключён</span>}
                </div>
                <div className="operator-details">
                  <span>{op.email}</span>
                  {op.telegram_id && <span>TG: {op.telegram_id}</span>}
                  <span>
                    С {new Date(op.created_at).toLocaleDateString("ru-RU")}
                  </span>
                </div>
              </div>
              <div className="operator-actions">
                {currentUser?.id !== op.id && (
                  <button
                    className={`btn-toggle-op ${op.is_active ? "active" : ""}`}
                    onClick={() => handleToggleActive(op)}
                  >
                    {op.is_active ? "Отключить" : "Включить"}
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Новый менеджер</h2>

            {error && <div className="error">{error}</div>}

            <div className="form-group">
              <label>Имя *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder="Имя менеджера"
              />
            </div>
            <div className="form-group">
              <label>Email *</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) =>
                  setFormData({ ...formData, email: e.target.value })
                }
                placeholder="email@example.com"
              />
            </div>
            <div className="form-group">
              <label>Пароль * (мин. 8 символов)</label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) =>
                  setFormData({ ...formData, password: e.target.value })
                }
                placeholder="Пароль"
              />
            </div>
            <div className="form-group">
              <label>Telegram ID (для уведомлений)</label>
              <input
                type="text"
                value={formData.telegram_id}
                onChange={(e) =>
                  setFormData({ ...formData, telegram_id: e.target.value })
                }
                placeholder="Например: 123456789"
              />
            </div>
            <div className="form-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={formData.is_admin}
                  onChange={(e) =>
                    setFormData({ ...formData, is_admin: e.target.checked })
                  }
                />
                Права администратора
              </label>
            </div>
            <div className="modal-actions">
              <button
                className="btn-cancel"
                onClick={() => setShowAddModal(false)}
              >
                Отмена
              </button>
              <button className="btn-save" onClick={handleAdd}>
                Создать
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
