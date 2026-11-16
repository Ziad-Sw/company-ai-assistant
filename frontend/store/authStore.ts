import { create } from "zustand";
import { persist } from "zustand/middleware";

/** الجلسة زي ما supabase-js بيرجّعها — للعرض والـapi client بس، مش للتفويض. */
export type AuthSession = {
  userId: string;
  accessToken: string;
  expiresAt: number; // Unix ثواني — زي ما Supabase بيبعته
};

export type AuthProfile = {
  role: string;
  fullName: string;
};

type AuthState = {
  session: AuthSession | null;
  profile: AuthProfile | null;
  setSession: (session: AuthSession) => void;
  setProfile: (profile: AuthProfile) => void;
  clear: () => void;
};

/**
 * الـstore ده للعرض فقط (الـAvatar، إظهار قائمة الـadmin، منع وميض المحتوى
 * في الـroute guard). التفويض الفعلي بيحصل على الـbackend — الـrole من
 * profiles على السيرفر، والـ401 من أي endpoint هو الحكم النهائي.
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      session: null,
      profile: null,
      setSession: (session) => set({ session }),
      setProfile: (profile) => set({ profile }),
      clear: () => set({ session: null, profile: null }),
    }),
    {
      name: "auth",
      // الوظايف مش بيانات — بس اللي بيتخزن في localStorage هو الجلسة والبروفايل.
      partialize: (state) => ({ session: state.session, profile: state.profile }),
    }
  )
);
