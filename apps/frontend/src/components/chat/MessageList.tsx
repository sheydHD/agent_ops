"use client";

import { useEffect, useRef } from "react";
import type { Message as MessageType } from "@/types/chat";
import { Message } from "./Message";

interface MessageListProps {
  messages: MessageType[];
  isLoading: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="text-center">
          <div className="mb-3 text-4xl">🔍</div>
          <h3 className="mb-1 text-lg font-medium text-gray-700">
            AgentOps RAG Demo
          </h3>
          <p className="mb-4 max-w-md text-sm text-gray-500">
            Ask a question. Every LLM call and retrieval step is traced to{" "}
            <strong>Langfuse</strong> and evaluated by{" "}
            <strong>Arize Phoenix</strong> — all running locally.
          </p>
          <div className="flex justify-center gap-4 text-xs text-gray-400">
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-blue-400" />
              Langfuse :3100
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-orange-400" />
              Phoenix :6006
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-green-400" />
              Backend :8501
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4">
      <div className="space-y-4">
        {messages.map((msg) => (
          <Message key={msg.id} message={msg} />
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <div className="h-2 w-2 animate-pulse rounded-full bg-blue-400" />
            Thinking...
          </div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
