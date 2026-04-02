"use client";

import { useState, useEffect } from "react";
import type { PromptSummary } from "@/types/chat";
import { fetchPrompts } from "@/services/api";

interface PromptSelectorProps {
  selectedPrompt: string | undefined;
  onSelect: (promptName: string | undefined) => void;
}

export function PromptSelector({
  selectedPrompt,
  onSelect,
}: PromptSelectorProps) {
  const [prompts, setPrompts] = useState<PromptSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchPrompts()
      .then((res) => {
        if (!cancelled) {
          setPrompts(res.prompts);
          setError(false);
        }
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleRefresh = () => {
    setLoading(true);
    setError(false);
    fetchPrompts()
      .then((res) => {
        setPrompts(res.prompts);
        setError(false);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  if (loading) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-gray-400">
        <svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24" fill="none">
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        Loading prompts…
      </div>
    );
  }

  if (error) {
    return (
      <button
        onClick={handleRefresh}
        className="text-xs text-red-400 hover:text-red-500"
      >
        Failed to load prompts — retry
      </button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <label
        htmlFor="prompt-select"
        className="text-xs font-medium text-gray-500"
      >
        Prompt:
      </label>
      <select
        id="prompt-select"
        value={selectedPrompt ?? "__default__"}
        onChange={(e) =>
          onSelect(e.target.value === "__default__" ? undefined : e.target.value)
        }
        className="rounded border border-gray-300 bg-white px-2 py-1 text-xs text-gray-700 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
      >
        <option value="__default__">Default (built-in)</option>
        {prompts.map((p) => (
          <option key={p.name} value={p.name}>
            {p.name}
            {p.labels.length > 0 ? ` [${p.labels.join(", ")}]` : ""}
          </option>
        ))}
      </select>
      <button
        onClick={handleRefresh}
        title="Refresh prompts from Langfuse"
        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
      >
        <svg
          className="h-3.5 w-3.5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 2v6h-6" />
          <path d="M3 12a9 9 0 0115-6.7L21 8" />
          <path d="M3 22v-6h6" />
          <path d="M21 12a9 9 0 01-15 6.7L3 16" />
        </svg>
      </button>
    </div>
  );
}
