import { FormEvent, useState } from "react";
import { apiFetch, getCsrfToken } from "@shared/api/client";
import { formatCitation } from "./citations";
import { track } from "@shared/analytics/client";

type Citation = { document_id: string; document_name?: string; page_start: number; page_end: number };

function detectLanguage(value: string): "vi" | "en" | "other" {
  if (value.trim().length < 10) return "other";
  if (/[ăâđêôơưĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặ]/.test(value)) return "vi";
  return /\b(the|what|how|when|where|is|are)\b/i.test(value) ? "en" : "other";
}

export function ChatPage() {
  const [conversationId, setConversationId] = useState<string>();
  const [text, setText] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [busy, setBusy] = useState(false);

  const ask = async (event: FormEvent) => {
    event.preventDefault();
    if (!text.trim() || busy) return;
    setBusy(true); setAnswer(""); setCitations([]);
    track("question_submitted", { question_length: text.trim().length, language: detectLanguage(text), ready_doc_count: 0 });
    const cid = conversationId ?? (await apiFetch<{ conversation_id: string }>("/conversations", { method: "POST" })).conversation_id;
    setConversationId(cid);
    const response = await fetch(`/api/v1/conversations/${cid}/questions`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json", ...(getCsrfToken() ? { "X-CSRF-Token": getCsrfToken()! } : {}) },
      body: JSON.stringify({ text }),
    });
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (reader) {
      const item = await reader.read();
      if (item.done) break;
      buffer += decoder.decode(item.value, { stream: true });
      const events = buffer.split("\n\n"); buffer = events.pop() ?? "";
      for (const raw of events) {
        const type = raw.match(/^event: (\w+)/m)?.[1];
        const data = raw.match(/^data: (.+)$/m)?.[1];
        if (!data) continue;
        const parsed = JSON.parse(data) as { text?: string; items?: Citation[] };
        if (type === "delta") setAnswer((current) => current + (parsed.text ?? ""));
        if (type === "citations") setCitations(parsed.items ?? []);
      }
    }
    setBusy(false);
  };
  return <section aria-label="Hỏi đáp">
    <h2>Hỏi về tài liệu</h2>
    <div className="answer" data-testid="answer-message" aria-live="polite">{answer || (busy ? "Đang tìm trong tài liệu…" : "Đặt câu hỏi để bắt đầu.")}</div>
    {citations.length > 0 && <ul>{citations.map((c, i) => <li data-testid="citation-chip" key={`${c.document_id}-${i}`} onClick={() => track("citation_viewed", { citation_index: i + 1 })}>Nguồn {i + 1}: {formatCitation(c.document_name ?? "Tài liệu", c.page_start, c.page_end)}</li>)}</ul>}
    <form onSubmit={ask} className="chat-composer">
      <textarea data-testid="question-input" value={text} maxLength={2000} onChange={(e) => setText(e.target.value)} disabled={busy} placeholder="Nhập câu hỏi…" />
      <button type="submit" disabled={busy || !text.trim()}>Gửi</button>
    </form>
  </section>;
}
