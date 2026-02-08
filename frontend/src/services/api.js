import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
});

// Добавляем JWT токен к каждому запросу
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Если 401 — выкидываем на логин
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// --- Auth ---
export const login = (email, password) =>
  api.post("/auth/login", { email, password });

export const getMe = () => api.get("/auth/me");

// --- Conversations ---
export const getConversations = (status, search) =>
  api.get("/conversations/", { params: { ...(status && { status }), ...(search && { search }) } });

export const getConversation = (id) => api.get(`/conversations/${id}`);

export const getStats = () => api.get("/conversations/stats");

export const updateConversation = (id, data) =>
  api.patch(`/conversations/${id}`, data);

// --- Messages ---
export const getMessages = (conversationId) =>
  api.get(`/conversations/${conversationId}/messages/`);

export const sendMessage = (conversationId, text) =>
  api.post(`/conversations/${conversationId}/messages/`, { text });

// --- Knowledge Base ---
export const getKnowledgeEntries = () => api.get("/knowledge");

export const createKnowledgeEntry = (question, answer) =>
  api.post("/knowledge", { question, answer });

export const updateKnowledgeEntry = (id, data) =>
  api.put(`/knowledge/${id}`, data);

export const deleteKnowledgeEntry = (id) => api.delete(`/knowledge/${id}`);

export default api;
