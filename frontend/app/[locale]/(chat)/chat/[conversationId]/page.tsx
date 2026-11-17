"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";

import { Button } from "@/components/ui/Button";
import { ChatComposer } from "@/features/chat/components/ChatComposer";
import { MessageList } from "@/features/chat/components/MessageList";
import { useChat } from "@/features/chat/hooks/useChat";
import { useModels } from "@/features/chat/hooks/useModels";
import { useChatStore } from "@/store/chatStore";

/**
 * محادثة قديمة مفتوحة من الـsidebar — الـhistory بيتجاب من GET
 * /conversations/{id} (بيأكد الملكية على الـbackend)، وكمّل رسايل live
 * بنفس الـflow بتاع المحادثة الجديدة.
 */
export default function ConversationPage() {
  const t = useTranslations("chat");
  const router = useRouter();
  const locale = useLocale();
  const params = useParams<{ conversationId: string }>();
  const conversationId = params.conversationId;
  const setActiveConversation = useChatStore((state) => state.setActiveConversation);
  const models = useModels();
  const chat = useChat({
    conversationId,
    model: models.selectedModel,
    reloadModels: models.reload,
  });

  useEffect(() => {
    setActiveConversation(conversationId);
    return () => {
      setActiveConversation(null);
    };
  }, [conversationId, setActiveConversation]);

  if (chat.historyState === "loading") {
    return (
      <div className="flex h-full items-center justify-center px-4">
        <p className="text-sm text-muted" aria-live="polite">
          {t("loading")}
        </p>
      </div>
    );
  }

  if (chat.historyState === "notFound" || chat.historyState === "failed") {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 px-4 text-center">
        <p role="alert" className="text-sm text-error">
          {chat.historyState === "notFound" ? t("errors.conversationNotFound") : t("errors.conversationLoadFailed")}
        </p>
        <Button variant="secondary" onClick={() => router.push(`/${locale}/chat`)}>
          {t("errors.backToChat")}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="min-h-0 flex-1">
        <MessageList messages={chat.messages} />
      </div>
      <ChatComposer
        models={models.models}
        modelsLoadFailed={models.loadFailed}
        selectedModel={models.selectedModel}
        onSelectModel={models.setSelectedModel}
        isStreaming={chat.isStreaming}
        onSend={chat.sendMessage}
        notice={chat.notice}
      />
    </div>
  );
}
