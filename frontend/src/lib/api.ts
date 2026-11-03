import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

export interface Source {
  title: string;
  url: string;
  score?: number;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  sources?: Source[];
}

export interface AskResponse {
  user_id: string;
  question: string;
  answer: string;
  sources: Source[];
  timestamp: string;
}

export interface HistoryResponse {
  user_id: string;
  messages: Message[];
}

export async function askQuestion(
  userId: string,
  question: string
): Promise<AskResponse> {
  const { data } = await api.post<AskResponse>("/api/ask", {
    user_id: userId,
    question,
  });
  return data;
}

export async function getHistory(userId: string): Promise<HistoryResponse> {
  const { data } = await api.get<HistoryResponse>(`/api/history/${userId}`);
  return data;
}

export async function clearHistory(userId: string): Promise<void> {
  await api.delete(`/api/history/${userId}`);
}
