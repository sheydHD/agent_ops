"use client";

import { useChat } from "@/hooks/useChat";
import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";
import { PromptSelector } from "./PromptSelector";

export function ChatInterface() {
  const { messages, isLoading, send, clearMessages, promptName, setPromptName } =
    useChat();

  return (
    <div className="flex h-[calc(100vh-80px)] flex-col rounded-lg border border-gray-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-gray-700">
            RAG Chat + AgentOps
          </h2>
          <p className="text-xs text-gray-400">
            Langfuse traces · Phoenix evaluation · OTel metrics
          </p>
        </div>
        <div className="flex items-center gap-3">
          <PromptSelector
            selectedPrompt={promptName}
            onSelect={setPromptName}
          />
          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              className="rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 hover:text-gray-700"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <MessageList messages={messages} isLoading={isLoading} />

      {/* Input */}
      <MessageInput onSend={send} isLoading={isLoading} />
    </div>
  );
}
