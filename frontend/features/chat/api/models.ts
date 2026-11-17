import { apiJson } from "@/lib/api/client";

/** موديل مجاني من GET /models — backend/app/api/models.py. */
export type ChatModel = {
  id: string;
  name: string;
  context_length: number | null;
};

export function listModels(): Promise<ChatModel[]> {
  return apiJson<ChatModel[]>("/models");
}
