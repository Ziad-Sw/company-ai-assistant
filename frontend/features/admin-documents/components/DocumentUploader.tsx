"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";

import { CategoryPicker } from "./CategoryPicker";
import { MAX_UPLOAD_MB } from "../types";

export type UploaderState = {
  /** upload = مستند جديد (بياخد category)، replace = استبدال نسخة موجودة. */
  mode: "upload" | "replace";
  documentId?: string;
  documentTitle?: string;
  documentVersion?: string;
};

type DocumentUploaderProps = {
  state: UploaderState;
  onClose: () => void;
  onSubmit: (file: File, category: string) => Promise<void>;
};

/**
 * DocumentUploader (PRD 10.5-ب) — اختيار ملف (PDF/DOCX/Markdown/TXT) +
 * اختيار الـcategory يدوياً (قرار PRD) في وضع الرفع. بيتتركب بس لما مفتوح
 * (الـparent بيعمل render مشروط) فالحالة بتبدأ نظيفة كل مرة. تحقق مبكر
 * قبل الإرسال: الامتداد المدعوم والحجم ≤ 20MB (نفس حدود الـbackend) عشان
 * رسالة خطأ أسرع من الـ422.
 */
export function DocumentUploader({ state, onClose, onSubmit }: DocumentUploaderProps) {
  const t = useTranslations("adminDocuments.uploader");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [category, setCategory] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isReplace = state.mode === "replace";

  const supportedExtensions = [".md", ".pdf", ".docx", ".txt"];

  function validateAndSubmit() {
    const file = fileInputRef.current?.files?.[0];
    if (!file) {
      setValidationError(t("noFile"));
      return;
    }
    const extension = `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`;
    if (!supportedExtensions.includes(extension)) {
      setValidationError(t("wrongExtension"));
      return;
    }
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setValidationError(t("tooLarge", { maxMb: MAX_UPLOAD_MB }));
      return;
    }
    if (!isReplace && !category) {
      setValidationError(t("missingCategory"));
      return;
    }
    setValidationError(null);
    setIsSubmitting(true);
    void onSubmit(file, category ?? "").finally(() => setIsSubmitting(false));
  }

  return (
    <Modal
      open
      onClose={() => (isSubmitting ? undefined : onClose())}
      title={isReplace
        ? t("replaceTitle", { title: state.documentTitle ?? "", version: state.documentVersion ?? "" })
        : t("uploadTitle")}
    >
      <div className="flex flex-col gap-4">
        {isReplace ? (
          <p className="text-sm text-muted">{t("replaceHint")}</p>
        ) : (
          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-foreground">{t("categoryLabel")}</span>
            <CategoryPicker value={category} onChange={setCategory} disabled={isSubmitting} />
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-foreground">{t("fileLabel")}</span>
          {/* الـinput الأصلي مخفي — زرار مخصص مكانه عشان مكان "No file chosen"
              بتاع المتصفح، وبعده اسم الملف المختار بس لما يختار فعلاً. */}
          <input
            ref={fileInputRef}
            id="admin-document-file"
            type="file"
            accept={supportedExtensions.join(",")}
            disabled={isSubmitting}
            className="sr-only"
            onChange={(event) => setFileName(event.target.files?.[0]?.name ?? null)}
          />
          <div className="flex items-center gap-3">
            <Button
              variant="secondary"
              size="sm"
              disabled={isSubmitting}
              onClick={() => fileInputRef.current?.click()}
            >
              {t("chooseFile")}
            </Button>
            {fileName ? (
              <span className="min-w-0 truncate text-sm text-foreground">{fileName}</span>
            ) : null}
          </div>
          <p className="text-xs text-muted">{t("fileHint", { maxMb: MAX_UPLOAD_MB })}</p>
        </div>

        {validationError ? (
          <p role="alert" className="text-sm text-error">{validationError}</p>
        ) : null}

        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose} disabled={isSubmitting}>
            {t("cancel")}
          </Button>
          <Button onClick={validateAndSubmit} loading={isSubmitting}>
            {isReplace ? t("submitReplace") : t("submitUpload")}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
