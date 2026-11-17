"use client";

import { useEffect, useRef } from "react";
import { useTranslations } from "next-intl";

import { cn } from "@/lib/utils";

type ModalProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  /** حجم اللوحة — الرفع/التأكيد sm، سجلات الـaudit والنسخ lg. */
  wide?: boolean;
  children: React.ReactNode;
};

/**
 * Modal من الـDesign-System (Tech-Stack §9 /components/ui): overlay غامق +
 * لوحة bg-surface بحد وradius-lg. بيتقفل بالـEscape والنقر بره، وبياخد
 * الـfocus أول ما يفتح (لوحة dialog أصلية مش <dialog> — من غير
 * showModal عشان نتحكم في الستايل على HTML خفيف متوافق).
 */
export function Modal({ open, onClose, title, wide = false, children }: ModalProps) {
  const t = useTranslations("common.modal");
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    panelRef.current?.focus();
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
        className={cn(
          `flex max-h-[85dvh] w-full flex-col overflow-y-auto rounded-[var(--radius-lg)] border border-border bg-surface p-5 shadow-xl
          outline-none focus-visible:outline-2 focus-visible:outline-primary/40`,
          wide ? "max-w-2xl" : "max-w-md"
        )}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 className="text-base font-semibold text-foreground">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label={t("close")}
            className="flex size-8 shrink-0 items-center justify-center rounded-[var(--radius-sm)] text-muted
              hover:bg-primary-subtle hover:text-foreground focus-visible:outline-2
              focus-visible:outline-offset-0 focus-visible:outline-primary/30"
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 6l12 12M18 6 6 18" strokeLinecap="round" />
            </svg>
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
