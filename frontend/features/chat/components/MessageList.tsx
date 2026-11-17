"use client";

import { useEffect, useRef } from "react";
import { useTranslations } from "next-intl";

import { MessageBubble } from "./MessageBubble";

import type { ChatMessage } from "../types";

/**
 * قائمة الرسايل مع auto-scroll لآخر رسالة — role=log عشان الـscreen reader
 * يعلن الرسايل الجديدة (الـaria-live=polite جواها).
 */
export function MessageList({ messages }: { messages: ChatMessage[] }) {
  const t = useTranslations("chat");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = scrollRef.current;
    if (element) element.scrollTo({ top: element.scrollHeight });
  }, [messages]);

  return (
    <div
      ref={scrollRef}
      role="log"
      aria-label={t("messagesLabel")}
      className="h-full overflow-y-auto px-4 py-6"
    >
      <div className="mx-auto flex max-w-3xl flex-col gap-3">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
      </div>
    </div>
  );
}
