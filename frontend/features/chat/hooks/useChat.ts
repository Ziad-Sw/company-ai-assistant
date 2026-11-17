"use client";

import { useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/api/client";
import { useChatStore } from "@/store/chatStore";

import { streamChat } from "../api/chat";
import { getConversation } from "@/features/conversations/api/conversations";

import type { ChatMessage } from "../types";
import type { ChatModel } from "../api/models";

/** تنبيه فوق شريط الإدخال — النص في الـmessages حسب النوع. */
export type ChatNotice = "modelUnavailable" | "sendFailed";

/** حالة تحميل الـhistory للمحادثة الموجودة. */
export type HistoryState = "loading" | "ready" | "notFound" | "failed";

type UseChatParams = {
  /** null = محادثة جديدة — أول رد هيرجّع الـid من الـheader. */
  conversationId: string | null;
  model: string | null;
  /** إعادة جلب قائمة الموديلات على 422 (الموديل اختفى من المجانية). */
  reloadModels: () => Promise<ChatModel[]>;
  /** بينداي أول ما محادثة جديدة تتحفظ — الصفحة بتحدّث الـURL بيها. */
  onConversationCreated?: (conversationId: string) => void;
};

function newMessageId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

/**
 * دورة حياة محادثة واحدة: تحميل الـhistory (لو محادثة موجودة)، وإرسال الرسايل،
 * وتطبيق events الـSSE (token/done/denied/error) على قائمة الرسايل.
 * الحفظ والحفظ على الـbackend — هنا عرض وترتيب بس.
 */
export function useChat({ conversationId, model, reloadModels, onConversationCreated }: UseChatParams) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [historyState, setHistoryState] = useState<HistoryState>(conversationId ? "loading" : "ready");
  const [isStreaming, setIsStreaming] = useState(false);
  const [notice, setNotice] = useState<ChatNotice | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const bumpConversations = useChatStore((state) => state.bumpConversations);

  // إلغاء الـstream لو الصفحة اتقفلت أو اتبدلت محادثة — من غيره الـfetch بيكمل في الخلفية.
  useEffect(() => () => abortRef.current?.abort(), []);

  // الـhistory للمحادثة الموجودة — مرة واحدة على التركيب (صفحة جديدة mount).
  useEffect(() => {
    if (conversationId === null) return;
    let cancelled = false;
    getConversation(conversationId)
      .then((detail) => {
        if (cancelled) return;
        setMessages(
          detail.messages.map((message) => ({
            id: message.id,
            role: message.role,
            content: message.content,
            sources: message.role === "assistant" ? (message.sources as ChatMessage["sources"]) : null,
          }))
        );
        setHistoryState("ready");
      })
      .catch((error) => {
        if (cancelled) return;
        setHistoryState(error instanceof ApiError && error.status === 404 ? "notFound" : "failed");
      });
    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  async function sendMessage(text: string) {
    if (!model || isStreaming || historyState !== "ready") return;
    const assistantId = newMessageId();
    setMessages((previous) => [
      ...previous,
      { id: newMessageId(), role: "user", content: text, sources: null },
      { id: assistantId, role: "assistant", content: "", sources: null },
    ]);
    setIsStreaming(true);
    setNotice(null);

    const controller = new AbortController();
    abortRef.current = controller;
    const updateAssistant = (patch: (message: ChatMessage) => ChatMessage) =>
      setMessages((previous) => previous.map((message) => (message.id === assistantId ? patch(message) : message)));

    try {
      const { conversationId: createdId } = await streamChat({
        message: text,
        model,
        conversationId,
        signal: controller.signal,
        onEvent: (event) => {
          if (event.type === "token") {
            updateAssistant((message) => ({ ...message, content: message.content + event.text }));
          } else if (event.type === "done") {
            updateAssistant((message) => ({ ...message, sources: event.sources }));
          } else if (event.type === "denied") {
            updateAssistant((message) => ({ ...message, content: event.message, state: "denied" }));
          } else {
            updateAssistant((message) => ({ ...message, state: "error" }));
          }
        },
      });
      if (conversationId === null && createdId) {
        bumpConversations();
        onConversationCreated?.(createdId);
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 422) {
        // الموديل المختار اختفى من المجانية (PRD 10.4) — بنجيب القائمة من جديد
        // ونبلغ المستخدم، ومسودته محفوظة في مربع الكتابة.
        await reloadModels().catch(() => undefined);
        setNotice("modelUnavailable");
      } else if (error instanceof DOMException && error.name === "AbortError") {
        return; // إلغاء مقصود (تنقّل/تقفيل) — مفيش حاجة نعملها.
      } else {
        setNotice("sendFailed");
      }
      // فشل قبل ما الـstream يبدأ: نشيل الـplaceholder الفاضي بتاع الرد.
      setMessages((previous) => previous.filter((message) => !(message.id === assistantId && message.content === "")));
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }

  return { messages, historyState, isStreaming, notice, sendMessage };
}
