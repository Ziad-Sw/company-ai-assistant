/** أنواع الموظفين — مطابقة لـbackend/app/api/admin_employees.py (EmployeeSummary/EmployeeCredentials). */

export type EmployeeRole = "sales" | "hr" | "admin";

export const EMPLOYEE_ROLES: EmployeeRole[] = ["sales", "hr", "admin"];

export type EmployeeSummary = {
  id: string;
  full_name: string;
  role: string;
  email: string | null;
  created_at: string;
};

/** الكريدنشيالز المؤقتة — بتظهر مرة واحدة في الـresponse (وفي المودال). */
export type EmployeeCredentials = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  temp_password: string;
};

/** جسم POST /admin/employees — الـemail local-part بس، الدومين من الـbackend. */
export type EmployeeCreate = {
  full_name: string;
  role: EmployeeRole;
  email_local: string;
};

/** نفس pattern الـbackend (`_EMAIL_LOCAL_PATTERN`) — تحقق مبكر قبل الإرسال. */
export const EMAIL_LOCAL_PATTERN = /^[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])$/;
