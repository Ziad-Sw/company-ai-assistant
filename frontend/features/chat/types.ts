import type { ChatSource } from "./api/chat";

/** رسالة في واجهة الشات — جاية من الـhistory أو live من الـstream. */
export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  /** null = لسه مفيش sources (streaming أو رسالة user أو فشل قبل الـdone). */
  sources: ChatSource[] | null;
  /** حالة خاصة للـassistant — denied ببتعرض كرسالة رفض وerror كملاحظة خطأ. */
  state?: "denied" | "error";
};
