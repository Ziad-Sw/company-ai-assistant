"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";

import { LanguageSwitcher } from "@/components/shared/LanguageSwitcher";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import { Button } from "@/components/ui/Button";
import { ListIcon, LogOutIcon, PanelToggleIcon, PlusIcon, UsersIcon } from "@/components/ui/icons";
import { cn } from "@/lib/utils";
import { Link } from "@/i18n/navigation";
import { supabase } from "@/features/auth/api/supabase";
import { ConversationList } from "@/features/conversations/components/ConversationList";
import { useAuthStore } from "@/store/authStore";
import { useChatStore } from "@/store/chatStore";

type SidebarProps = {
  /** ظهور الـpanel المحسوب من الـlayout (طي على الديسكتوب / drawer على الموبايل). */
  open: boolean;
  /** حالة طي الديسكتوب — بتتحكم في ظهور زرار الطي والـicon بتاعته. */
  collapsed: boolean;
  onClose: () => void;
  onCollapse: () => void;
};

/**
 * الـsidebar المشترك (Tech-Stack قسم 9: components/shared) — خلفية bg-sidebar
 * بعرض 280px: فوق الهوية + زرار طي/فتح دائري (زي Gemini)، زرار "+ New Chat"
 * ثابت فوق القائمة، قايمة المحادثات، وتسجيل الخروج مثبّت آخر الـpanel كـdanger
 * (Design-System: Sidebar + Button). على الموبايل drawer بـoverlay.
 */
export function Sidebar({ open, collapsed, onClose, onCollapse }: SidebarProps) {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("chat");
  const tSidebar = useTranslations("common.sidebar");
  const fullName = useAuthStore((state) => state.profile?.fullName ?? "");
  const role = useAuthStore((state) => state.profile?.role ?? "");
  const setActiveConversation = useChatStore((state) => state.setActiveConversation);

  function handleNewChat() {
    onClose();
    setActiveConversation(null);
    router.push(`/${locale}/chat`);
  }

  function handleSignOut() {
    onClose();
    // onAuthStateChange هيمسح الـstore، والـRequireAuth بيرجّع المستخدم
    // لصفحة الدخول بنفسه — مفيش navigation يدوي هنا.
    void supabase.auth.signOut();
  }

  return (
    <>
      {/* الـoverlay للموبايل بس — على الديسكتوب الـpanel بيتنقل في الـflex. */}
      <div
        aria-hidden="true"
        onClick={onClose}
        className={cn(
          "fixed inset-0 z-30 bg-black/40 md:hidden",
          open ? "block" : "hidden"
        )}
      />
      <aside
        aria-label={t("sidebar.listLabel")}
        className={cn(
          // position منطقي (start) عشان الـsidebar يبقى على أول السطر في الاتنين —
          // والـtranslate فيزيائي فبيتقلب بالـrtl:/ltr: عشان يختفي بره الشاشة.
          "fixed inset-y-0 start-0 z-40 flex w-[280px] flex-col border-e border-border bg-sidebar",
          "transition-transform duration-200 md:static md:z-auto",
          collapsed
            ? "max-md:ltr:-translate-x-full max-md:rtl:translate-x-full md:hidden"
            : open
              ? "translate-x-0"
              : "max-md:ltr:-translate-x-full max-md:rtl:translate-x-full"
        )}
      >
        <div className="flex items-center gap-3 border-b border-border px-4 py-4">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-foreground">{fullName}</p>
            <p className="truncate text-xs text-muted">{role}</p>
          </div>
          <button
            type="button"
            onClick={onCollapse}
            aria-label={t("sidebar.collapseSidebar")}
            aria-expanded={!collapsed}
            className="hidden md:flex size-9 shrink-0 items-center justify-center rounded-[var(--radius-md)] text-muted
              hover:bg-primary-subtle hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-primary/30"
          >
            <PanelToggleIcon className="rtl:-scale-x-100" />
          </button>
        </div>

        <div className="px-3 pt-3">
          <Button variant="secondary" size="md" className="w-full" onClick={handleNewChat}>
            <span className="flex items-center justify-center gap-2">
              <PlusIcon />
              {t("sidebar.newChat")}
            </span>
          </Button>
        </div>

        <nav className="min-h-0 flex-1 overflow-y-auto p-3">
          {/* قسم الـadmin — بيظهر لحساب الـadmin بس (PRD 10.5/10.6: صفحات الإدارة). */}
          {role === "admin" ? (
            <div className="mb-3 border-b border-border pb-3">
              <p className="px-2 pb-1 text-xs font-medium text-muted">{tSidebar("adminSection")}</p>
              <Link
                href="/admin/documents"
                onClick={onClose}
                className="flex items-center gap-2 rounded-[var(--radius-md)] px-2 py-2 text-sm text-foreground
                  hover:bg-primary-subtle focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-primary/30"
              >
                <ListIcon />
                {tSidebar("adminDocuments")}
              </Link>
              <Link
                href="/admin/employees"
                onClick={onClose}
                className="flex items-center gap-2 rounded-[var(--radius-md)] px-2 py-2 text-sm text-foreground
                  hover:bg-primary-subtle focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-primary/30"
              >
                <UsersIcon />
                {tSidebar("adminEmployees")}
              </Link>
            </div>
          ) : null}
          <ConversationList />
        </nav>

        <div className="border-t border-border p-3">
          {/* تفضيلات الموظف جنب هوية/خروج — العنوان بياخد عرضه كامل فوق بدون زحمة. */}
          <div className="mb-2 grid grid-cols-2 gap-2">
            <ThemeToggle />
            <LanguageSwitcher />
          </div>
          <Button variant="danger" size="md" className="w-full" onClick={handleSignOut}>
            <LogOutIcon className="rtl:-scale-x-100" />
            {t("signOut")}
          </Button>
        </div>
      </aside>
    </>
  );
}
