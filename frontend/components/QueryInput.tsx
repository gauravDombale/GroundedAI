"use client";

import { useState, useRef, KeyboardEvent } from "react";

interface QueryInputProps {
  onSubmit: (query: string) => void;
  isLoading: boolean;
}

export default function QueryInput({ onSubmit, isLoading }: QueryInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;
    onSubmit(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleInput = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  };

  return (
    <div
      style={{
        display: "flex",
        gap: "10px",
        alignItems: "flex-end",
        background: "var(--bg-input)",
        border: "1px solid var(--border)",
        borderRadius: "16px",
        padding: "10px 14px",
        transition: "border-color 0.2s",
      }}
      onFocus={(e) => {
        (e.currentTarget as HTMLDivElement).style.borderColor = "var(--accent-primary)";
        (e.currentTarget as HTMLDivElement).style.boxShadow = "0 0 0 3px rgba(99,102,241,0.1)";
      }}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) {
          (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border)";
          (e.currentTarget as HTMLDivElement).style.boxShadow = "none";
        }
      }}
    >
      <textarea
        ref={textareaRef}
        id="query-input"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        placeholder="Ask a question about your documents… (Enter to send, Shift+Enter for newline)"
        rows={1}
        style={{
          flex: 1,
          background: "transparent",
          border: "none",
          outline: "none",
          color: "var(--text-primary)",
          fontSize: "15px",
          resize: "none",
          lineHeight: 1.6,
          fontFamily: "var(--font-inter)",
          maxHeight: "180px",
          overflowY: "auto",
        }}
      />
      <button
        id="submit-query-btn"
        onClick={handleSubmit}
        disabled={!value.trim() || isLoading}
        style={{
          width: "40px",
          height: "40px",
          borderRadius: "10px",
          background:
            value.trim() && !isLoading
              ? "linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))"
              : "var(--bg-card)",
          border: "1px solid var(--border)",
          color: value.trim() && !isLoading ? "#fff" : "var(--text-muted)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: value.trim() && !isLoading ? "pointer" : "not-allowed",
          transition: "all 0.2s",
          flexShrink: 0,
          fontSize: "16px",
        }}
        aria-label="Send message"
      >
        {isLoading ? (
          <div
            style={{
              width: "16px",
              height: "16px",
              border: "2px solid var(--text-muted)",
              borderTopColor: "var(--accent-primary)",
              borderRadius: "50%",
              animation: "spin 0.8s linear infinite",
            }}
          />
        ) : (
          "↑"
        )}
      </button>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
