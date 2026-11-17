import { RequireAdmin } from "@/features/auth/components/RequireAuth";
import { AppShell } from "@/components/shared/AppShell";

/**
 * بوابهة + هيكل صفحات الـadmin (Phase 3 — PRD 10.5/10.6): الحماية
 * admin-only، وبعدها نفس هيكل الـchat (sidebar قابل للطي + drawer موبايل).
 */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAdmin>
      <AppShell>{children}</AppShell>
    </RequireAdmin>
  );
}
