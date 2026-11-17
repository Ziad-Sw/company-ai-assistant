"use client";

import { useTranslations } from "next-intl";

import { Input } from "@/components/ui/Input";

import { CategoryPicker } from "./CategoryPicker";
import type { DocumentsController } from "../hooks/useDocuments";

/**
 * صف الفلاتر (PRD 10.5-أ: فلترة بالـcategory والبحث بالاسم) — البحث بيتأجل
 * بـdebounce جوه الـhook، والـcategory بيرفرش فوراً.
 */
export function DocumentFilters({ controller }: { controller: DocumentsController }) {
  const t = useTranslations("adminDocuments");

  return (
    <div className="grid gap-2 sm:grid-cols-[minmax(0,220px)_1fr]">
      <CategoryPicker
        includeAll
        value={controller.category}
        onChange={controller.setCategory}
        disabled={controller.isLoading}
      />
      <Input
        type="search"
        value={controller.searchInput}
        onChange={(event) => controller.setSearchInput(event.target.value)}
        placeholder={t("filters.searchPlaceholder")}
        aria-label={t("filters.searchAriaLabel")}
        disabled={controller.isLoading}
      />
    </div>
  );
}
