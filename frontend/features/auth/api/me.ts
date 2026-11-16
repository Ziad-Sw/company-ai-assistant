import { apiJson } from "@/lib/api/client";
import type { MeResponse } from "../types";

/** GET /me — الـrole والاسم من السيرفر بعد ما الـJWT يتحقق (مش من الـclient). */
export function fetchMe(): Promise<MeResponse> {
  return apiJson<MeResponse>("/me");
}
