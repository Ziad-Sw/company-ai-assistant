"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";

import { ChatBubbleIcon } from "@/components/ui/icons";
import { ChatComposer } from "@/features/chat/components/ChatComposer";
import { MessageList } from "@/features/chat/components/MessageList";
import { useChat } from "@/features/chat/hooks/useChat";
import { useModels } from "@/features/chat/hooks/useModels";
import { useChatStore } from "@/store/chatStore";

/** صفحة محادثة جديدة — بعد أول رد الـURL بيتحدّث للمحادثة المحفوظة. */
export default function NewChatPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("chat");
  const setActiveConversation = useChatStore((state) => state.setActiveConversation);
  const models = useModels();
  const chat = useChat({
    conversationId: null,
    model: models.selectedModel,
    reloadModels: models.reload,
    onConversationCreated: (conversationId) => {
      setActiveConversation(conversationId);
      router.replace(`/${locale}/chat/${conversationId}`);
    },
  });

  useEffect(() => {
    setActiveConversation(null);
  }, [setActiveConversation]);

  return (
    <div className="flex h-full flex-col">
      {chat.messages.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 px-4 text-center">
          <ChatBubbleIcon size="lg" className="text-muted" />
          <h1 className="text-lg font-semibold text-foreground">{t("newChatTitle")}</h1>
          <p className="max-w-md text-sm text-muted">{t("newChatBody")}</p>
        </div>
      ) : (
        <div className="min-h-0 flex-1">
          <MessageList messages={chat.messages} />
        </div>
      )}
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
