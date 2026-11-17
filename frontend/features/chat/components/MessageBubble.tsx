"use client";

import { useTranslations } from "next-intl";

import { cn } from "@/lib/utils";
import { MarkdownContent } from "./MarkdownContent";
import { PermissionDeniedMessage } from "./PermissionDeniedMessage";

import type { ChatMessage } from "../types";

function SourceBadges({ message }: { message: ChatMessage }) {
  const t = useTranslations("chat.sources");
  if (message.sources === null || message.sources.length === 0) return null;
  return (
    <ul className="mt-2 flex flex-wrap gap-1.5" aria-label={t("label")}>
      {message.sources.map((source) => (
        <li
          key={source.chunk_id}
          className="rounded-[var(--radius-full)] border border-border bg-page px-2 py-0.5 text-xs text-muted"
          title={t("sourceTitle", { title: source.doc_title, version: source.version })}
        >
          <span className="line-clamp-1 max-w-64" translate="no">
            {source.doc_title}
          </span>
          <span className="ms-1 text-muted">{source.version}</span>
        </li>
      ))}
    </ul>
  );
}

function StreamingDots() {
  return (
    <span className="flex items-center gap-1 py-1.5" aria-hidden="true">
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          style={{ animationDelay: `${index * 150}ms` }}
          className="size-1.5 animate-bounce rounded-full bg-muted"
        />
      ))}
    </span>
  );
}

/**
 * فقاعة رسالة واحدة (Design-System: Chat Message Bubble) — رسالة الموظف
 * على الـinline-end بخلفية primary، ورد الـAI على العكس بـbg-surface وحدود.
 * الـstreaming بيظهر 3 نقط لحد أول token، والمصادر badges تحت الرد.
 */
export function MessageBubble({ message }: { message: ChatMessage }) {
  const t = useTranslations("chat");

  if (message.role === "user") {
    return (
      <div className="ms-auto max-w-[85%] rounded-[var(--radius-md)] bg-primary px-4 py-2.5">
        <p className="whitespace-pre-wrap break-words text-base text-on-primary">{message.content}</p>
      </div>
    );
  }

  if (message.state === "denied") {
    return <PermissionDeniedMessage message={message.content} />;
  }

  const isStreaming = message.sources === null && message.state === undefined;

  return (
    <div
      className={cn(
        "me-auto max-w-[85%] rounded-[var(--radius-md)] border border-border bg-surface px-4 py-2.5",
        isStreaming && "min-w-16"
      )}
    >
      {message.content ? (
        <MarkdownContent content={message.content} />
      ) : isStreaming ? (
        <StreamingDots />
      ) : null}
      {message.state === "error" ? (
        <p role="alert" className="text-sm text-error">
          {t("errors.model")}
        </p>
      ) : null}
      <SourceBadges message={message} />
    </div>
  );
}
