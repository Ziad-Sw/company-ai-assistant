"use client";

import { useCallback, useEffect, useState } from "react";

import { createEmployee, listEmployees } from "../api/employees";
import type { EmployeeCreate, EmployeeCredentials, EmployeeSummary } from "../types";

/**
 * حالة شاشة الموظفين: القايمة + الإضافة. الـloading مشتق من employees === null
 * (نمط useModels/useDocuments)، والجلب في effect بـpromise callback بس
 * (مفيش setState متزامن). مفيش polling — الحالة هنا فورية (الإنشاء متزامن).
 */
export function useEmployees() {
  // null = جاري التحميل الأولي — مش نفس القايمة الفاضية بعد الفشل
  const [employees, setEmployees] = useState<EmployeeSummary[] | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isAdding, setIsAdding] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listEmployees()
      .then((list) => {
        if (cancelled) return;
        setEmployees(list);
        setLoadFailed(false);
      })
      .catch(() => {
        if (cancelled) return;
        setEmployees([]);
        setLoadFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  /** إعادة جلب يدوية (زرار retry) — event handler فالـsetState المتزامن مسموح فيه. */
  const reload = useCallback(async () => {
    try {
      const list = await listEmployees();
      setEmployees(list);
      setLoadFailed(false);
    } catch {
      setLoadFailed(true);
    }
  }, []);

  /** إنشاء موظف — بيرجّع الكريدنشيالز للمودال، والخطأ بيتعرض في الـbanner.
   *  بعد النجاح بنجيب القايمة من السيرفر تاني (الـresponse مفيهوش created_at —
   *  ممنوع نصنع بيانات محلياً). */
  const add = useCallback(async (payload: EmployeeCreate): Promise<EmployeeCredentials> => {
    setActionError(null);
    setIsAdding(true);
    try {
      const credentials = await createEmployee(payload);
      try {
        const list = await listEmployees();
        setEmployees(list);
        setLoadFailed(false);
      } catch {
        // القايمة هتتظبط مع أي reload — فشلها مش بيلغي نجاح الإنشاء
      }
      return credentials;
    } catch (error) {
      setActionError(error instanceof Error ? error.message : String(error));
      throw error;
    } finally {
      setIsAdding(false);
    }
  }, []);

  return {
    employees: employees ?? [],
    isLoading: employees === null,
    loadFailed,
    reload: () => void reload(),
    actionError,
    clearActionError: () => setActionError(null),
    isAdding,
    add,
  };
}

export type EmployeesController = ReturnType<typeof useEmployees>;
