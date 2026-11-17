import { apiFetch, ApiError } from "@/lib/api/client";

/** مصدر الإجابة زي ما /chat بيرجّعه في event: done — من backend/app/api/chat.py. */
export type ChatSource = {
  chunk_id: string;
  doc_id: string;
  doc_title: string;
  version: string;
  section: unknown;
  similarity_score: number;
};

/** Events الـSSE بتوع POST /chat — الـdata في كل event JSON في سطر واحد. */
export type ChatStreamEvent =
  | { type: "token"; text: string }
  | { type: "done"; sources: ChatSource[] }
  | { type: "denied"; message: string }
  | { type: "error"; message: string };

export type StreamChatParams = {
  message: string;
  model: string;
  conversationId: string | null;
  signal: AbortSignal;
  onEvent: (event: ChatStreamEvent) => void;
};

/** زوج event/data من block واحد في الـstream. */
function parseSseBlock(block: string): { event: string; data: string } | null {
  let event: string | null = null;
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice("event:".length).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice("data:".length).trimStart());
  }
  if (event === null || dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}

/**
 * بعت سؤال لـPOST /chat وقراية الـstream حتة حتة — نفس الـfetch wrapper
 * (Authorization + silent refresh + redirect على 401) والـbody بيتقري يدوي
 * عشان الـSSE. الـconversation_id بتاع المحادثة الجديدة بيرجع في
 * header ‏X-Conversation-Id فبنرجّعه للـcaller.
 */
export async function streamChat({
  message,
  model,
  conversationId,
  signal,
  onEvent,
}: StreamChatParams): Promise<{ conversationId: string | null }> {
  const response = await apiFetch("/chat", {
    method: "POST",
    body: JSON.stringify({ message, model, conversation_id: conversationId }),
    signal,
  });

  if (!response.ok) {
    const detail = await response
      .json()
      .then((body) => (typeof body?.detail === "string" ? body.detail : null))
      .catch(() => null);
    throw new ApiError(response.status, detail ?? `POST /chat failed with ${response.status}.`);
  }

  const newConversationId = response.headers.get("X-Conversation-Id");
  const body = response.body;
  if (!body) {
    throw new ApiError(500, "الرد مفيهوش stream — مش قادرين نعرض الإجابة.");
  }

  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      // الـevents بتتقسم بـسطرين فاضيين — آخر block قبل الـdone ممكن يكون لسه ناقص.
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";
      for (const block of blocks) {
        const parsed = parseSseBlock(block);
        if (!parsed) continue;
        let payload: Record<string, unknown>;
        try {
          payload = JSON.parse(parsed.data) as Record<string, unknown>;
        } catch {
          continue;
        }
        switch (parsed.event) {
          case "token":
            onEvent({ type: "token", text: String(payload.text ?? "") });
            break;
          case "done":
            onEvent({ type: "done", sources: (payload.sources as ChatSource[]) ?? [] });
            break;
          case "denied":
            onEvent({ type: "denied", message: String(payload.message ?? "") });
            break;
          case "error":
            onEvent({ type: "error", message: String(payload.message ?? "") });
            break;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  return { conversationId: newConversationId };
}
