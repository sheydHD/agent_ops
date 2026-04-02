"use client";

import { useState, useCallback } from "react";
import type { Message, MessageMetadata } from "@/types/chat";
import { sendMessage } from "@/services/api";
import { generateId } from "@/lib/utils";

// Stable anonymous user ID for the browser session
const SESSION_USER_ID =
  typeof window !== "undefined"
    ? `user-${crypto.randomUUID().slice(0, 8)}`
    : "user-ssr";

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [userId] = useState(SESSION_USER_ID);
  const [promptName, setPromptName] = useState<string | undefined>();

  const send = useCallback(
    async (text: string) => {
      const MAX_MESSAGE_LENGTH = 5000;
      if (!text.trim() || isLoading) return;
      if (text.trim().length > MAX_MESSAGE_LENGTH) {
        const errorMsg: Message = {
          id: generateId(),
          role: "system",
          content: `Message too long. Maximum ${MAX_MESSAGE_LENGTH} characters allowed.`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMsg]);
        return;
      }

      // Add user message
      const userMsg: Message = {
        id: generateId(),
        role: "user",
        content: text.trim(),
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);

      try {
        const response = await sendMessage({
          message: text.trim(),
          conversation_id: conversationId,
          user_id: userId,
          prompt_name: promptName,
        });

        setConversationId(response.conversation_id);

        const assistantMsg: Message = {
          id: generateId(),
          role: "assistant",
          content: response.message,
          timestamp: new Date(response.timestamp),
          metadata: response.metadata,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        const errorMsg: Message = {
          id: generateId(),
          role: "system",
          content:
            err instanceof Error
              ? `Error: ${err.message}`
              : "An unexpected error occurred. Is the backend running?",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, conversationId, userId, promptName]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setConversationId(undefined);
  }, []);

  return { messages, isLoading, send, clearMessages, promptName, setPromptName };
}
