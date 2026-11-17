"use client";

import { useTranslations } from "next-intl";

import { ChatInput } from "./ChatInput";
import { ModelDropdown } from "./ModelDropdown";

import type { ChatNotice } from "../hooks/useChat";
import type { ChatModel } from "../api/models";

type ChatComposerProps = {
  models: ChatModel[] | null;
  modelsLoadFailed: boolean;
  selectedModel: string | null;
  onSelectModel: (modelId: string) => void;
  isStreaming: boolean;
  onSend: (text: string) => void;
  notice: ChatNotice | null;
};

/**
 * شريط الإرسال المشترك بين المحادثة الجديدة والمحادثة المفتوحة:
 * اختيار الموديل + مربع الكتابة + تنبيه فوقهم (إلغاء الموديل/فشل الإرسال).
 */
export function ChatComposer({
  models,
  modelsLoadFailed,
  selectedModel,
  onSelectModel,
  isStreaming,
  onSend,
  notice,
}: ChatComposerProps) {
  const t = useTranslations("chat");

  return (
    <div className="mx-auto w-full max-w-3xl px-4 pb-4">
      {notice !== null ? (
        <p role="alert" className="mb-2 rounded-[var(--radius-sm)] bg-warning-subtle px-3 py-2 text-sm text-warning">
          {notice === "modelUnavailable" ? t("notices.modelUnavailable") : t("notices.sendFailed")}
        </p>
      ) : null}
      <div className="mb-2 w-72">
        <ModelDropdown
          models={models}
          loadFailed={modelsLoadFailed}
          selectedModel={selectedModel}
          onSelect={onSelectModel}
        />
      </div>
      <ChatInput disabled={isStreaming} onSend={onSend} />
    </div>
  );
}
