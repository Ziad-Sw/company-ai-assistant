import { apiFetch, apiJson } from "@/lib/api/client";

import type { AuditEntry, DocumentPatch, DocumentSummary } from "../types";

/** نداءات endpoints إدارة المستندات — backend/app/api/admin_documents.py (9 endpoints). */

export function listDocuments(category: string | null, search: string | null): Promise<DocumentSummary[]> {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (search) params.set("search", search);
  const query = params.toString();
  return apiJson<DocumentSummary[]>(`/admin/documents${query ? `?${query}` : ""}`);
}

export function getDocument(documentId: string): Promise<DocumentSummary> {
  return apiJson<DocumentSummary>(`/admin/documents/${documentId}`);
}

/** الرفع/الاستبدال multipart — ممنوع نحدد Content-Type يدوي (الـboundary من الـbrowser). */
async function postDocumentForm(
  path: string,
  file: File,
  category?: string
): Promise<DocumentSummary> {
  const form = new FormData();
  form.append("file", file);
  if (category) form.append("category", category);
  const response = await apiFetch(path, { method: "POST", body: form });
  if (!response.ok) {
    const { errorMessageFrom } = await import("@/lib/api/client");
    throw new Error(await errorMessageFrom(response));
  }
  return response.json() as Promise<DocumentSummary>;
}

export function uploadDocument(file: File, category: string): Promise<DocumentSummary> {
  return postDocumentForm("/admin/documents", file, category);
}

export function replaceDocument(documentId: string, file: File): Promise<DocumentSummary> {
  return postDocumentForm(`/admin/documents/${documentId}/replace`, file);
}

export function reprocessDocument(documentId: string): Promise<DocumentSummary> {
  return apiJson<DocumentSummary>(`/admin/documents/${documentId}/reprocess`, { method: "POST" });
}

export function patchDocument(documentId: string, patch: DocumentPatch): Promise<DocumentSummary> {
  return apiJson<DocumentSummary>(`/admin/documents/${documentId}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export async function deleteDocument(documentId: string): Promise<void> {
  const response = await apiFetch(`/admin/documents/${documentId}`, { method: "DELETE" });
  if (!response.ok && response.status !== 404) {
    const { errorMessageFrom } = await import("@/lib/api/client");
    throw new Error(await errorMessageFrom(response));
  }
}

export function listDocumentVersions(documentId: string): Promise<DocumentSummary[]> {
  return apiJson<DocumentSummary[]>(`/admin/documents/${documentId}/versions`);
}

export function listDocumentAudit(documentId: string): Promise<AuditEntry[]> {
  return apiJson<AuditEntry[]>(`/admin/documents/${documentId}/audit`);
}
