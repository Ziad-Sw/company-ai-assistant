"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { listConversations } from "../api/conversations";
import { ConversationItem } from "./ConversationItem";
import { useChatStore } from "@/store/chatStore";

import type { ConversationSummary } from "../api/conversations";

/**
 * قائمة محادثات الموظف (الأحدث أول — زي ما الـbackend بيرجّعها) للـsidebar.
 * بتعمل refetch لما conversationsVersion يتزوّد (محادثة جديدة اتضافت).
 */
export function ConversationList() {
  const t = useTranslations("chat.sidebar");
  const conversationsVersion = useChatStore((state) => state.conversationsVersion);
  const [conversations, setConversations] = useState<ConversationSummary[] | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listConversations()
      .then((result) => {
        if (!cancelled) {
          setConversations(result);
          setLoadFailed(false);
        }
      })
      .catch(() => {
        if (!cancelled) setLoadFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [conversationsVersion]);

  if (conversations === null) {
    return (
      <p className="px-3 py-2 text-sm text-muted" aria-live="polite">
        {t("loadingConversations")}
      </p>
    );
  }
  if (loadFailed) {
    return (
      <p className="px-3 py-2 text-sm text-error" role="alert">
        {t("loadFailed")}
      </p>
    );
  }
  if (conversations.length === 0) {
    return <p className="px-3 py-2 text-sm text-muted">{t("empty")}</p>;
  }
  return (
    <ul className="flex flex-col gap-1" aria-label={t("listLabel")}>
      {conversations.map((conversation) => (
        <li key={conversation.id}>
          <ConversationItem conversation={conversation} />
        </li>
      ))}
    </ul>
  );
}
