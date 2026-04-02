export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  metadata?: MessageMetadata;
}

export interface MessageMetadata {
  latency_ms?: number;
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
  token_efficiency?: number;
  retrieval_docs?: number;
  max_relevance?: number;
  route_type?: string;
  source_documents?: string[];
  trace_url?: string | null;
  phoenix_url?: string | null;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  user_id?: string;
  prompt_name?: string;
}

export interface ChatResponse {
  message: string;
  conversation_id: string;
  metadata: MessageMetadata;
  timestamp: string;
}

export interface PromptSummary {
  name: string;
  type: string;
  labels: string[];
  latest_version: number | null;
}

export interface PromptsListResponse {
  prompts: PromptSummary[];
}
