"use client";

import { EmployeesScreen } from "@/features/admin-employees/components/EmployeesScreen";

/**
 * صفحة إدارة الموظفين (Phase 3 — PRD 10.6) — الحماية في (admin)/layout.tsx
 * (RequireAdmin)، والشاشة كلها feature-local في features/admin-employees.
 */
export default function AdminEmployeesPage() {
  return <EmployeesScreen />;
}
