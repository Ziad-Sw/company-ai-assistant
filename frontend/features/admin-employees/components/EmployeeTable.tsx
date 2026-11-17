"use client";

import { useLocale, useTranslations } from "next-intl";

import { formatDateTime } from "@/lib/utils";

import type { EmployeeSummary } from "../types";

/**
 * جدول الموظفين (PRD 10.6) — الاسم + الدور + الإيميل + تاريخ الإضافة.
 * Phase 3 مفيهوش أكشنز على الصفوف (الإضافة بس) — التعديل/الحذف مراحل لاحقة.
 */
export function EmployeeTable({ employees }: { employees: EmployeeSummary[] }) {
  const t = useTranslations("adminEmployees");
  const locale = useLocale();

  return (
    <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-border bg-surface">
      <table className="w-full min-w-[640px] text-start text-sm">
        <thead>
          <tr className="border-b border-border text-xs text-muted">
            <th scope="col" className="px-4 py-3 text-start font-medium">{t("table.name")}</th>
            <th scope="col" className="px-4 py-3 text-start font-medium">{t("table.role")}</th>
            <th scope="col" className="px-4 py-3 text-start font-medium">{t("table.email")}</th>
            <th scope="col" className="px-4 py-3 text-start font-medium">{t("table.createdAt")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {employees.map((employee) => (
            <tr key={employee.id} className="text-foreground">
              <td className="max-w-[240px] px-4 py-3 font-medium">
                <p className="truncate">{employee.full_name}</p>
              </td>
              <td className="px-4 py-3">{t(`roles.${employee.role}`)}</td>
              <td className="max-w-[260px] px-4 py-3">
                <p className="truncate" dir="ltr">{employee.email ?? "—"}</p>
              </td>
              <td className="px-4 py-3 text-xs text-muted">
                {formatDateTime(employee.created_at, locale)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
