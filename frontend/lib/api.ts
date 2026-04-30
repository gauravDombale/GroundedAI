const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export interface AskResponse {
  query: string;
  rewritten_query: string;
  answer: string;
  citations: string[];
  latency_ms: number;
  cache_hit: boolean;
}

export async function askQuestion(query: string): Promise<AskResponse> {
  const response = await fetch(`${BACKEND_URL}/api/v1/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: 5, rewrite: true }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Backend error ${response.status}: ${error}`);
  }

  return response.json() as Promise<AskResponse>;
}

export async function retrieveChunks(
  query: string,
  topK = 5
): Promise<{ results: Array<{ chunk_id: string; text: string; score: number }> }> {
  const url = new URL(`${BACKEND_URL}/api/v1/retrieve`);
  url.searchParams.set("q", query);
  url.searchParams.set("top_k", String(topK));

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`Retrieval error ${response.status}`);
  return response.json();
}
