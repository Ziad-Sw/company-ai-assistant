import { RequireAdmin } from "@/features/auth/components/RequireAuth";

/**
 * بوابهة الـroute group بتاع /(admin)/* — صفحات Phase 3 (إدارة المستندات
 * وإضافة موظف) هتندرج تحتها مباشرة وهتلاقي الـguard جاهز.
 */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <RequireAdmin>{children}</RequireAdmin>;
}
