"use client";

import { DocumentsScreen } from "@/features/admin-documents/components/DocumentsScreen";

/**
 * صفحة إدارة المستندات (Phase 3 — PRD 10.5) — الحماية في (admin)/layout.tsx
 * (RequireAdmin)، والشاشة كلها feature-local في features/admin-documents.
 */
export default function AdminDocumentsPage() {
  return <DocumentsScreen />;
}
