import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "NEXT_PUBLIC_SUPABASE_URL وNEXT_PUBLIC_SUPABASE_ANON_KEY ناقصين في frontend/.env.local — انسخ .env.local.example واملا القيم."
  );
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    // silent refresh في الخلفية (القرار 5): الـtoken بيتجدد قبل ما يخلص،
    // وعند فشل الـrefresh الـclient بيعمل SIGNED_OUT ونسيب الـapi client يرد للمستخدم.
    persistSession: true,
    autoRefreshToken: true,
  },
});
