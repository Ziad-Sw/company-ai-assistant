/** أنواع المستندات — مطابقة لـbackend/app/db/document_store.py (DocumentSummary). */

export type DocumentStatus = "active" | "inactive" | "processing" | "failed";

export type DocumentCategory =
  | "property_listings"
  | "payment_policies"
  | "company_info_support";

/** نفس الـfrozenset في app.rag.retrieval — القايمة كاملة للـadmin. */
export const DOCUMENT_CATEGORIES: DocumentCategory[] = [
  "property_listings",
  "payment_policies",
  "company_info_support",
];

export type DocumentSummary = {
  id: string;
  doc_id: string;
  title: string;
  category: string;
  version: string;
  language: string;
  status: DocumentStatus;
  source_path: string | null;
  uploaded_by_name: string | null;
  updated_at: string;
  created_at: string;
};

/** سجل الـaudit — مطابق لـbackend/app/db/audit_store.py. */
export type AuditEntry = {
  id: string;
  actor_id: string | null;
  actor_name: string | null;
  action:
    | "upload"
    | "edit"
    | "replace"
    | "deactivate"
    | "activate"
    | "delete"
    | "reprocess"
    | "add_employee";
  target_type: "document" | "employee";
  target_id: string;
  created_at: string;
};

/** الحد من نفس backend/app/db/storage_files.py — تحقق مبكر قبل الرفع. */
export const MAX_UPLOAD_MB = 20;

/** جسم PATCH /admin/documents/{id} — الحالة بين active/inactive فقط. */
export type DocumentPatch = {
  category?: string;
  status?: "active" | "inactive";
};
