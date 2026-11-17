import { supabase } from "@/features/auth/api/supabase";
import { useAuthStore } from "@/store/authStore";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** بنعمل refresh قبل الـtoken يقرب على الخلاص بهالمقدار من الوقت (ثواني). */
const REFRESH_AHEAD_SECONDS = 30;

export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * الـaccess_token الحالي، مع silent refresh (القرار 5): لو الـtoken قرّب يخلص
 * بنعمل refresh قبل ما نستخدمه بدل ما نسيب الـrequest يروح ويرجع 401.
 */
async function currentAccessToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  const session = data.session;
  if (!session) return null;
  if (!session.expires_at || session.expires_at * 1000 - Date.now() >= REFRESH_AHEAD_SECONDS * 1000) {
    return session.access_token;
  }
  const { data: refreshed } = await supabase.auth.refreshSession();
  return refreshed.session?.access_token ?? session.access_token;
}

/** مسار الـlogin المحلي — من أول segment في الـpath عشان نحافظ على اللغة. */
function loginPath(): string {
  const locale = window.location.pathname.split("/")[1] || "en";
  return `/${locale}/login`;
}

/** نفضّي الجلسة ونرجّع للمستخدم صفحة الدخول — على فشل الـrefresh أو 401 من الـbackend. */
function resetSessionAndRedirectToLogin(): void {
  useAuthStore.getState().clear();
  void supabase.auth.signOut();
  window.location.assign(loginPath());
}

/**
 * الـfetch wrapper المشترك: بيضيف Authorization: Bearer من الجلسة الحالية،
 * وعلى 401 بيرجّع للمستخدم صفحة الدخول. بيرجّع الـResponse الخام عشان
 * نداءات الـstreaming (زي /chat بـSSE) تقدر تقرا الـbody على دفعات بنفس الهيدر.
 */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const accessToken = await currentAccessToken();
  if (!accessToken) {
    resetSessionAndRedirectToLogin();
    throw new ApiError(401, "مفيش جلسة نشطة — بنرجّعك لصفحة الدخول.");
  }

  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${accessToken}`);
  // الـFormData (رفع ملفات الـadmin) لازم يسيب الـbrowser يحدد الـContent-Type
  // بنفسه عشان يحط الـboundary بتاع الـmultipart.
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (response.status === 401) {
    // الجلسة انتهت والـrefresh فشل — نفضّي ونرجّع للدخول (القرار 5).
    resetSessionAndRedirectToLogin();
    throw new ApiError(401, "انتهت الجلسة — بنرجّعك لصفحة الدخول.");
  }
  return response;
}

/** نداءات JSON العادية — بترمي ApiError على أي status مش ناجح. */
export async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(path, init);
  if (!response.ok) {
    throw new ApiError(response.status, await errorMessageFrom(response));
  }
  return response.json() as Promise<T>;
}

/**
 * رسالة الخطأ اللي بتتعرض: الـdetail من الـbackend الأول (رسائل endpoints
 * الـadmin عربية وصريحة عن سبب الرفض — زي تضارب النسخ)، وgeneric احتياطي.
 */
export async function errorMessageFrom(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    if (body?.detail) return body.detail;
  } catch {
    // الـbody مش JSON — نرجّع الرسالة الافتراضية
  }
  return `الطلب فشل بـ${response.status}.`;
}
