"use client";

import { useState, useRef, useEffect } from "react";
import ChatMessage from "@/components/ChatMessage";
import QueryInput from "@/components/QueryInput";
import SystemStatus from "@/components/SystemStatus";
import { AskResponse, askQuestion } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: string[];
  latencyMs?: number;
  isLoading?: boolean;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (query: string) => {
    if (!query.trim() || isLoading) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: query,
    };

    const loadingMsg: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      isLoading: true,
    };

    setMessages((prev) => [...prev, userMsg, loadingMsg]);
    setIsLoading(true);

    try {
      const response: AskResponse = await askQuestion(query);
      setMessages((prev) =>
        prev.map((m) =>
          m.isLoading
            ? {
                ...m,
                content: response.answer,
                citations: response.citations,
                latencyMs: response.latency_ms,
                isLoading: false,
              }
            : m
        )
      );
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.isLoading
            ? {
                ...m,
                content:
                  "⚠️ Failed to get an answer. Please ensure the backend is running.",
                isLoading: false,
              }
            : m
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([]);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      {/* Header */}
      <header
        style={{
          borderBottom: "1px solid var(--border)",
          background: "var(--bg-secondary)",
          padding: "0 24px",
          height: "64px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          position: "sticky",
          top: 0,
          zIndex: 50,
          backdropFilter: "blur(12px)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "10px",
              background: "linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "18px",
              animation: "pulse-glow 3s ease-in-out infinite",
            }}
          >
            🔍
          </div>
          <div>
            <h1 style={{ fontSize: "17px", fontWeight: 700, letterSpacing: "-0.3px" }}>
              Ask My Docs
            </h1>
            <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "1px" }}>
              Hybrid RAG · Citation-Grounded
            </p>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {messages.length > 0 && (
            <button
              id="clear-chat-btn"
              onClick={handleClear}
              style={{
                background: "transparent",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
                padding: "6px 14px",
                borderRadius: "8px",
                fontSize: "13px",
                cursor: "pointer",
                transition: "all 0.2s",
              }}
              onMouseEnter={(e) => {
                (e.target as HTMLButtonElement).style.borderColor = "var(--error)";
                (e.target as HTMLButtonElement).style.color = "var(--error)";
              }}
              onMouseLeave={(e) => {
                (e.target as HTMLButtonElement).style.borderColor = "var(--border)";
                (e.target as HTMLButtonElement).style.color = "var(--text-secondary)";
              }}
            >
              Clear
            </button>
          )}
          <SystemStatus />
        </div>
      </header>

      {/* Main Content */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", maxWidth: "860px", margin: "0 auto", width: "100%", padding: "0 20px" }}>
        {messages.length === 0 ? (
          <WelcomeScreen onExampleClick={handleSubmit} />
        ) : (
          <div style={{ flex: 1, paddingTop: "24px", paddingBottom: "24px" }}>
            {messages.map((msg, idx) => (
              <ChatMessage key={msg.id} message={msg} isLast={idx === messages.length - 1} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </main>

      {/* Input area */}
      <div
        style={{
          borderTop: "1px solid var(--border)",
          background: "var(--bg-secondary)",
          padding: "16px 20px",
          position: "sticky",
          bottom: 0,
        }}
      >
        <div style={{ maxWidth: "860px", margin: "0 auto" }}>
          <QueryInput onSubmit={handleSubmit} isLoading={isLoading} />
        </div>
      </div>
    </div>
  );
}

function WelcomeScreen({ onExampleClick }: { onExampleClick: (q: string) => void }) {
  const examples = [
    "What is Retrieval-Augmented Generation?",
    "How does hybrid retrieval work?",
    "What are the evaluation thresholds for the CI gate?",
    "Explain cross-encoder reranking.",
  ];

  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 0",
        textAlign: "center",
      }}
    >
      <div
        style={{
          width: "72px",
          height: "72px",
          borderRadius: "20px",
          background: "linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "32px",
          marginBottom: "24px",
          boxShadow: "0 0 40px rgba(99,102,241,0.4)",
        }}
      >
        🔍
      </div>
      <h2 style={{ fontSize: "28px", fontWeight: 800, letterSpacing: "-0.5px", marginBottom: "12px" }}>
        Ask anything about your docs
      </h2>
      <p style={{ color: "var(--text-secondary)", fontSize: "15px", maxWidth: "480px", lineHeight: 1.7, marginBottom: "40px" }}>
        Powered by hybrid BM25 + vector retrieval, cross-encoder reranking, and citation-grounded generation. Every answer comes with verified sources.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "12px",
          width: "100%",
          maxWidth: "600px",
        }}
      >
        {examples.map((ex, i) => (
          <button
            key={i}
            id={`example-${i}`}
            onClick={() => onExampleClick(ex)}
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "12px",
              padding: "14px 16px",
              color: "var(--text-secondary)",
              fontSize: "13px",
              textAlign: "left",
              cursor: "pointer",
              transition: "all 0.2s",
              lineHeight: 1.5,
            }}
            onMouseEnter={(e) => {
              const el = e.currentTarget;
              el.style.borderColor = "var(--accent-primary)";
              el.style.color = "var(--text-primary)";
              el.style.background = "var(--bg-input)";
            }}
            onMouseLeave={(e) => {
              const el = e.currentTarget;
              el.style.borderColor = "var(--border)";
              el.style.color = "var(--text-secondary)";
              el.style.background = "var(--bg-card)";
            }}
          >
            <span style={{ fontSize: "16px", marginRight: "8px" }}>→</span>
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
