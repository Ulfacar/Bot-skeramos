import { useCallback, useEffect, useRef, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { getMe, getConversations } from "./services/api";
import LoginPage from "./pages/LoginPage";
import ConversationsPage from "./pages/ConversationsPage";
import ChatPage from "./pages/ChatPage";
import KnowledgePage from "./pages/KnowledgePage";

function PrivateRoute({ children }) {
  const [checking, setChecking] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setChecking(false);
      return;
    }
    getMe()
      .then(() => setAuthenticated(true))
      .catch(() => localStorage.removeItem("token"))
      .finally(() => setChecking(false));
  }, []);

  if (checking) return <p className="loading">Загрузка...</p>;
  if (!authenticated) return <Navigate to="/login" />;
  return children;
}

function playNotificationSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    oscillator.connect(gain);
    gain.connect(ctx.destination);
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(880, ctx.currentTime);
    oscillator.frequency.setValueAtTime(660, ctx.currentTime + 0.1);
    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
    oscillator.start(ctx.currentTime);
    oscillator.stop(ctx.currentTime + 0.3);
  } catch (e) {
    // Web Audio API not available
  }
}

export default function App() {
  const [needsOperatorCount, setNeedsOperatorCount] = useState(0);
  const prevCountRef = useRef(0);
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("token");
    window.location.href = "/login";
  };

  const pollNeedsOperator = useCallback(async () => {
    if (!localStorage.getItem("token")) return;
    try {
      const res = await getConversations("needs_operator");
      const count = res.data.length;
      if (count > prevCountRef.current) {
        playNotificationSound();
      }
      prevCountRef.current = count;
      setNeedsOperatorCount(count);
    } catch (e) {
      // ignore polling errors
    }
  }, []);

  useEffect(() => {
    pollNeedsOperator();
    const interval = setInterval(pollNeedsOperator, 10000);
    return () => clearInterval(interval);
  }, [pollNeedsOperator]);

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-logo-wrapper" onClick={() => navigate("/?filter=needs_operator")} style={{ cursor: "pointer" }}>
          <span className="app-logo">SKERAMOS</span>
          {needsOperatorCount > 0 && (
            <span className="notification-badge">{needsOperatorCount}</span>
          )}
        </div>
        {localStorage.getItem("token") && (
          <div className="header-buttons">
            <button className="btn-knowledge" onClick={() => navigate("/knowledge")}>
              📚 База знаний
            </button>
            <button className="btn-logout" onClick={handleLogout}>
              Выйти
            </button>
          </div>
        )}
      </header>

      <main className="app-main">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <ConversationsPage />
              </PrivateRoute>
            }
          />
          <Route
            path="/chat/:id"
            element={
              <PrivateRoute>
                <ChatPage />
              </PrivateRoute>
            }
          />
          <Route
            path="/knowledge"
            element={
              <PrivateRoute>
                <KnowledgePage />
              </PrivateRoute>
            }
          />
        </Routes>
      </main>
    </div>
  );
}
