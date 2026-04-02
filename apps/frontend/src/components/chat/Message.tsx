"use client";

import type { Message as MessageType } from "@/types/chat";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import { formatLatency } from "@/lib/utils";

interface MessageProps {
  message: MessageType;
}

export function Message({ message }: MessageProps) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  return (
    <div
      className={`animate-fadeIn flex ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-[85%] rounded-lg px-4 py-3 ${
          isUser
            ? "bg-primary-600 text-white"
            : isSystem
              ? "border border-red-200 bg-red-50 text-red-700"
              : "border border-gray-200 bg-gray-50 text-gray-800"
        }`}
      >
        {/* Message content */}
        {isUser ? (
          <p className="text-sm">{message.content}</p>
        ) : (
          <div className="markdown-content prose prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* Metadata bar for assistant messages */}
        {message.metadata && (
          <div className="mt-3 border-t border-gray-200 pt-2">
            {/* Metrics row */}
            <div className="flex flex-wrap gap-3 text-xs text-gray-500">
              {message.metadata.latency_ms != null && (
                <span title="End-to-end latency">
                  ⏱ {formatLatency(message.metadata.latency_ms)}
                </span>
              )}
              {message.metadata.total_tokens != null &&
                message.metadata.total_tokens > 0 && (
                  <span title="Token usage: input → output">
                    🔤 {message.metadata.input_tokens}→
                    {message.metadata.output_tokens} (
                    {message.metadata.total_tokens})
                  </span>
                )}
              {message.metadata.token_efficiency != null &&
                message.metadata.token_efficiency > 0 && (
                  <span title="Output/Input token ratio">
                    📊 eff: {message.metadata.token_efficiency.toFixed(2)}
                  </span>
                )}
              {message.metadata.retrieval_docs != null &&
                message.metadata.retrieval_docs > 0 && (
                  <span title="Documents retrieved from vector store">
                    📄 {message.metadata.retrieval_docs} docs
                  </span>
                )}
            </div>

            {/* Trace links */}
            <div className="mt-1 flex flex-wrap gap-3 text-xs">
              {message.metadata.trace_url && (
                <a
                  href={message.metadata.trace_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 underline hover:text-blue-800"
                >
                  View Langfuse Trace ↗
                </a>
              )}
              {message.metadata.phoenix_url && (
                <a
                  href={message.metadata.phoenix_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-orange-600 underline hover:text-orange-800"
                >
                  View Phoenix Traces ↗
                </a>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
