import { apiFetch, apiJson } from "@/lib/api/client";

import type { EmployeeCreate, EmployeeCredentials, EmployeeSummary } from "../types";

/** نداءات endpoints إدارة الموظفين — backend/app/api/admin_employees.py (GET/POST). */

export function listEmployees(): Promise<EmployeeSummary[]> {
  return apiJson<EmployeeSummary[]>("/admin/employees");
}

export async function createEmployee(payload: EmployeeCreate): Promise<EmployeeCredentials> {
  const response = await apiFetch("/admin/employees", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const { errorMessageFrom } = await import("@/lib/api/client");
    throw new Error(await errorMessageFrom(response));
  }
  return response.json() as Promise<EmployeeCredentials>;
}
