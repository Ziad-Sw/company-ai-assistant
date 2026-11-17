import { AppShell } from "@/components/shared/AppShell";

/** هيكل صفحات الـchat — نفس الهيكل المشترك مع الـadmin (AppShell). */
export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
