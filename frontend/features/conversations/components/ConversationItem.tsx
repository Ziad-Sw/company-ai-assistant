"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";

import { cn } from "@/lib/utils";
import { useChatStore } from "@/store/chatStore";

import type { ConversationSummary } from "../api/conversations";

function relativeTime(iso: string, locale: string): string {
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(diffMs / 60_000);
  if (Math.abs(minutes) < 60) return formatter.format(-minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return formatter.format(-hours, "hour");
  return formatter.format(-Math.round(hours / 24), "day");
}

/**
 * عنصر محادثة في الـsidebar — عنوان مختصر + hover، والمحادثة النشطة
 * عليها primary-subtle (Design-System: Sidebar).
 */
export function ConversationItem({ conversation }: { conversation: ConversationSummary }) {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("chat.sidebar");
  const isActive = useChatStore((state) => state.activeConversationId === conversation.id);

  return (
    <button
      type="button"
      onClick={() => {
        router.push(`/${locale}/chat/${conversation.id}`);
      }}
      aria-current={isActive ? "page" : undefined}
      className={cn(
        "w-full rounded-[var(--radius-md)] px-3 py-2 text-start text-sm transition-colors",
        "hover:bg-primary-subtle focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-primary/30",
        isActive ? "bg-primary-subtle font-medium text-foreground" : "text-foreground"
      )}
    >
      <span className="line-clamp-2">{conversation.title ?? t("untitled")}</span>
      <span className="mt-0.5 block text-xs text-muted">
        {relativeTime(conversation.created_at, locale)}
      </span>
    </button>
  );
}
