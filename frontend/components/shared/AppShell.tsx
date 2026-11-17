"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { PanelToggleIcon } from "@/components/ui/icons";
import { Sidebar } from "@/components/shared/Sidebar";

/**
 * هيكل الصفحات المشترك (chat + admin): الـsidebar ثابت على الديسكتوب (وقابل
 * للطي بزرار الطي زي Gemini — لما يتطيّر زرار دائري صغير فوق يفتحه تاني)،
 * وعلى الموبايل drawer بيزرّ من زرار قائمة. المحتوى نفسه في الصفحات
 * (children). اتسحب من (chat)/layout.tsx لما صفحات الـadmin احتاجت نفس
 * الهيكل — بدون تكرار.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const t = useTranslations("common.sidebar");
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="flex h-dvh overflow-hidden bg-page">
      <Sidebar
        open={drawerOpen}
        collapsed={collapsed}
        onClose={() => setDrawerOpen(false)}
        onCollapse={() => setCollapsed(true)}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-2 border-b border-border bg-surface px-3 py-2 md:hidden">
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            aria-label={t("openMenu")}
            aria-expanded={drawerOpen}
            className="flex size-9 items-center justify-center rounded-[var(--radius-md)] text-foreground
              hover:bg-primary-subtle focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-primary/30"
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
            </svg>
          </button>
          <span className="text-sm font-medium text-foreground" translate="no">
            Reel Estate
          </span>
        </header>
        <div className="relative min-h-0 flex-1">
          {collapsed ? (
            <button
              type="button"
              onClick={() => setCollapsed(false)}
              aria-label={t("showSidebar")}
              className="absolute start-2 top-2 z-10 flex size-9 items-center justify-center rounded-[var(--radius-md)] text-muted
                hover:bg-primary-subtle hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-primary/30"
            >
              <PanelToggleIcon className="rtl:-scale-x-100" />
            </button>
          ) : null}
          {children}
        </div>
      </div>
    </div>
  );
}
