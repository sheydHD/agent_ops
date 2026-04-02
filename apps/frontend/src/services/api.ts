import axios from "axios";
import type { ChatRequest, ChatResponse, PromptsListResponse } from "@/types/chat";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8501";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120_000, // 2 min — LLM inference can be slow on local hardware
  headers: { "Content-Type": "application/json" },
});

export async function sendMessage(
  request: ChatRequest
): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>("/api/chat", request);
  return data;
}

export async function checkHealth(): Promise<Record<string, unknown>> {
  const { data } = await api.get("/health");
  return data;
}

export async function fetchPrompts(): Promise<PromptsListResponse> {
  const { data } = await api.get<PromptsListResponse>("/api/prompts");
  return data;
}
