import { apiJson } from "@/lib/api/client";

/** محادثة من GET /conversations — backend/app/db/conversation_store.py. */
export type ConversationSummary = {
  id: string;
  title: string | null;
  created_at: string;
};

export type StoredMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: Record<string, unknown>[];
  created_at: string;
};

export type ConversationDetail = ConversationSummary & {
  messages: StoredMessage[];
};

export function listConversations(): Promise<ConversationSummary[]> {
  return apiJson<ConversationSummary[]>("/conversations");
}

export function getConversation(conversationId: string): Promise<ConversationDetail> {
  return apiJson<ConversationDetail>(`/conversations/${conversationId}`);
}
