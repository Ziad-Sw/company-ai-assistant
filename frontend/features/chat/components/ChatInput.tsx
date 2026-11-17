"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";

/** الحد الأقصى للرسالة — نفس MESSAGE_MAX_CHARS في backend/app/api/chat.py. */
const MESSAGE_MAX_CHARS = 4000;

type ChatInputProps = {
  disabled: boolean;
  onSend: (text: string) => void;
};

/**
 * مربع كتابة الرسالة: textarea بيكبر مع النص، Enter يبعت (Shift+Enter سطر
 * جديد)، والزرار معطّل أثناء الـstreaming أو لما النص فاضي.
 */
export function ChatInput({ disabled, onSend }: ChatInputProps) {
  const t = useTranslations("chat");
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const canSend = !disabled && value.trim().length > 0;

  function resize() {
    const element = textareaRef.current;
    if (element) {
      element.style.height = "auto";
      element.style.height = `${Math.min(element.scrollHeight, 200)}px`;
    }
  }

  function submit() {
    if (!canSend) return;
    onSend(value.trim());
    setValue("");
    requestAnimationFrame(resize);
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    // الـEnter أثناء تركيب الحروف العربي (IME) مش إرسال.
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <div className="flex items-end gap-2">
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        maxLength={MESSAGE_MAX_CHARS}
        placeholder={t("inputPlaceholder")}
        aria-label={t("inputLabel")}
        disabled={disabled}
        spellCheck={false}
        onChange={(event) => {
          setValue(event.target.value);
          resize();
        }}
        onKeyDown={handleKeyDown}
        className="max-h-[200px] min-h-10 flex-1 resize-none rounded-[var(--radius-md)] border border-border-strong bg-input px-3 py-2 text-base text-foreground
          placeholder:text-muted focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-primary/30 focus-visible:border-primary
          disabled:opacity-50"
      />
      <button
        type="button"
        onClick={submit}
        disabled={!canSend}
        aria-label={t("send")}
        className="flex size-10 shrink-0 items-center justify-center rounded-[var(--radius-md)] bg-primary text-on-primary
          hover:bg-primary-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary
          disabled:pointer-events-none disabled:opacity-50"
      >
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className="size-5 rtl:-scale-x-100"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M5 12h14m0 0-6-6m6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
    </div>
  );
}
