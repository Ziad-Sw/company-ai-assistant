"use client";

import { useCallback, useEffect, useState } from "react";

import {
  deleteDocument,
  getDocument,
  listDocuments,
  patchDocument,
  reprocessDocument,
  replaceDocument,
  uploadDocument,
} from "../api/documents";
import type { DocumentPatch, DocumentSummary } from "../types";

const POLL_INTERVAL_MS = 2000;
const SEARCH_DEBOUNCE_MS = 400;

/**
 * حالة شاشة المستندات كلها: القائمة + الفلاتر + الأكشنز + الـpolling.
 * الـloading مشتق من documents === null (نمط useModels)، والجلب الأولي
 * بيتنفذ في effect بـpromise callback بس (مفيش setState متزامن).
 * الـpolling للـprocessing بس: كل ثانيتين بيجيب صفوف processing ويدمج
 * حالتها — لما مفيش processing الموقّف كله (مفيش interval دائم).
 */
export function useDocuments() {
  // null = جاري التحميل الأولي — مش نفس القايمة الفاضية بعد الفشل
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [category, setCategory] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyDocumentId, setBusyDocumentId] = useState<string | null>(null);

  // جلب القايمة حسب الفلتر — الـsetState كله جوه callbacks الـpromise
  // (النمط المقبول في eslint react-hooks/set-state-in-effect).
  useEffect(() => {
    let cancelled = false;
    listDocuments(category, search)
      .then((list) => {
        if (cancelled) return;
        setDocuments(list);
        setLoadFailed(false);
      })
      .catch(() => {
        if (cancelled) return;
        setDocuments([]);
        setLoadFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [category, search]);

  // الـdebounce بتاع البحث: بنكتب في searchInput فوراً، والـsearch الفعلي بيتحدث بعد سكون.
  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput.trim()), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [searchInput]);

  /** إعادة جلب يدوية (زرار retry) — event handler فالـsetState المتزامن مسموح فيه. */
  const reload = useCallback(async () => {
    try {
      const list = await listDocuments(category, search);
      setDocuments(list);
      setLoadFailed(false);
    } catch {
      setLoadFailed(true);
    }
  }, [category, search]);

  // دمج صف أو أكتر في القائمة حسب الـid — كل الأكشنز بتستخدمه بعد الـresponse.
  const mergeDocument = useCallback((updated: DocumentSummary) => {
    setDocuments((previous) => {
      if (!previous) return [updated];
      const index = previous.findIndex((document) => document.id === updated.id);
      if (index === -1) return [updated, ...previous];
      const next = [...previous];
      next[index] = updated;
      return next;
    });
  }, []);

  // الـpolling: شغال بس لما فيه processing — صف واحد اتحول active/failed خلاص وقف.
  const hasProcessing = (documents ?? []).some((document) => document.status === "processing");
  useEffect(() => {
    if (!hasProcessing || documents === null) return;
    const processingIds = documents
      .filter((document) => document.status === "processing")
      .map((document) => document.id);
    const timer = setTimeout(() => {
      void Promise.all(processingIds.map((id) => getDocument(id).catch(() => null))).then(
        (updated) => {
          setDocuments((previous) =>
            (previous ?? []).map(
              (document) => updated.find((row) => row?.id === document.id) ?? document
            )
          );
        }
      );
    }, POLL_INTERVAL_MS);
    return () => clearTimeout(timer);
  }, [documents, hasProcessing]);

  /** بيلف كل الأكشنز اللي بتعدّل صف واحد مع تعطيل الزرار وتصيير الخطأ. */
  const withRow = useCallback(
    async (documentId: string | null, action: () => Promise<DocumentSummary | void>) => {
      setActionError(null);
      setBusyDocumentId(documentId);
      try {
        const updated = await action();
        if (updated) mergeDocument(updated);
        // الحذف بيرجّع void — بيشيل الصف من القائمة
        else setDocuments((previous) => (previous ?? []).filter((row) => row.id !== documentId));
      } catch (error) {
        setActionError(error instanceof Error ? error.message : String(error));
      } finally {
        setBusyDocumentId(null);
      }
    },
    [mergeDocument]
  );

  const upload = useCallback(
    (file: File, selectedCategory: string) => withRow(null, () => uploadDocument(file, selectedCategory)),
    [withRow]
  );

  const replace = useCallback(
    (documentId: string, file: File) => withRow(documentId, () => replaceDocument(documentId, file)),
    [withRow]
  );

  const reprocess = useCallback(
    (documentId: string) => withRow(documentId, () => reprocessDocument(documentId)),
    [withRow]
  );

  const patch = useCallback(
    (documentId: string, patchPayload: DocumentPatch) =>
      withRow(documentId, () => patchDocument(documentId, patchPayload)),
    [withRow]
  );

  const remove = useCallback(
    (documentId: string) => withRow(documentId, () => deleteDocument(documentId)),
    [withRow]
  );

  return {
    documents: documents ?? [],
    isLoading: documents === null,
    loadFailed,
    reload: () => void reload(),
    category,
    setCategory,
    searchInput,
    setSearchInput,
    actionError,
    clearActionError: () => setActionError(null),
    busyDocumentId,
    upload,
    replace,
    reprocess,
    patch,
    remove,
  };
}

export type DocumentsController = ReturnType<typeof useDocuments>;
