/** أنواع الـauth feature — اللي بتجي من الـbackend مش من الـclient. */

/** رد GET /me — المصدر الوحيد للـrole والاسم (مش الـtoken payload). */
export type MeResponse = {
  user_id: string;
  role: string;
  full_name: string;
};
