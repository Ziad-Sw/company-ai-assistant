"use client";

import { useEffect, useState } from "react";

import { useChatStore } from "@/store/chatStore";

import { listModels } from "../api/models";

import type { ChatModel } from "../api/models";

/**
 * حالة اختيار الموديل (PRD 10.4): القائمة من GET /models، والاختيار في
 * الـchatStore. لو الموديل المختار اختفى من القائمة المجانية بنرجّع أول واحد
 * تلقائياً — و`reload` للـ422 بتاع /chat (الموديل باظ قبل الإرسال).
 */
export function useModels() {
  const selectedModel = useChatStore((state) => state.selectedModel);
  const setSelectedModel = useChatStore((state) => state.setSelectedModel);
  const [models, setModels] = useState<ChatModel[] | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listModels()
      .then((result) => {
        if (cancelled) return;
        setModels(result);
        applyList(result, selectedModel, setSelectedModel);
      })
      .catch(() => {
        if (!cancelled) setLoadFailed(true);
      });
    return () => {
      cancelled = true;
    };
    // الجلب مرة واحدة عند التركيب — الـselectedModel المقروء وقتها كافي.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** إعادة جلب القائمة — بنستخدمها لما /chat يرفض الموديل المختار (422). */
  async function reload(): Promise<ChatModel[]> {
    const result = await listModels();
    setModels(result);
    setLoadFailed(false);
    applyList(result, selectedModel, setSelectedModel);
    return result;
  }

  return {
    models,
    loadFailed,
    selectedModel,
    setSelectedModel,
    reload,
  };
}

function applyList(
  models: ChatModel[],
  selectedModel: string | null,
  setSelectedModel: (model: string | null) => void
) {
  const stillValid = models.some((model) => model.id === selectedModel);
  if (!stillValid) {
    setSelectedModel(models[0]?.id ?? null);
  }
}
