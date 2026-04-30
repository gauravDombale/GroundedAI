"use client";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: string[];
  latencyMs?: number;
  isLoading?: boolean;
}

export default function ChatMessage({
  message,
  isLast,
}: {
  message: Message;
  isLast: boolean;
}) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div
        className="animate-fade-in-up"
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginBottom: "20px",
        }}
      >
        <div
          style={{
            maxWidth: "75%",
            background: "linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))",
            borderRadius: "18px 18px 4px 18px",
            padding: "12px 18px",
            color: "#fff",
            fontSize: "15px",
            lineHeight: 1.6,
            boxShadow: "0 4px 20px rgba(99,102,241,0.3)",
          }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div
      className={isLast ? "animate-fade-in-up" : ""}
      style={{ display: "flex", gap: "12px", marginBottom: "24px", alignItems: "flex-start" }}
    >
      {/* Avatar */}
      <div
        style={{
          width: "36px",
          height: "36px",
          borderRadius: "10px",
          background: "linear-gradient(135deg, #1e1b4b, #312e81)",
          border: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "16px",
          flexShrink: 0,
          marginTop: "2px",
        }}
      >
        🤖
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        {message.isLoading ? (
          <TypingIndicator />
        ) : (
          <>
            <div
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: "4px 18px 18px 18px",
                padding: "16px 20px",
                fontSize: "15px",
                lineHeight: 1.8,
                color: "var(--text-primary)",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {message.content}
            </div>

            {/* Citations */}
            {message.citations && message.citations.length > 0 && (
              <div style={{ marginTop: "10px", display: "flex", flexWrap: "wrap", gap: "6px", alignItems: "center" }}>
                <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.8px" }}>
                  Sources:
                </span>
                {message.citations.map((cite) => (
                  <span
                    key={cite}
                    style={{
                      background: "rgba(20, 184, 166, 0.1)",
                      border: "1px solid rgba(20, 184, 166, 0.3)",
                      color: "var(--accent-teal)",
                      borderRadius: "6px",
                      padding: "2px 8px",
                      fontSize: "12px",
                      fontWeight: 600,
                    }}
                  >
                    {cite}
                  </span>
                ))}
                {message.latencyMs !== undefined && (
                  <span style={{ marginLeft: "auto", fontSize: "11px", color: "var(--text-muted)" }}>
                    {message.latencyMs}ms
                  </span>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "4px 18px 18px 18px",
        padding: "16px 20px",
        display: "flex",
        gap: "6px",
        alignItems: "center",
      }}
    >
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="typing-dot"
          style={{
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            background: "var(--accent-primary)",
          }}
        />
      ))}
    </div>
  );
}
