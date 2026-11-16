"use client";

import { useAuthSync } from "../hooks/useAuth";

/** بيركب مستمع onAuthStateChange مرة واحدة على مستوى الـapp — مكون client صغير. */
export function SessionSync() {
  useAuthSync();
  return null;
}
