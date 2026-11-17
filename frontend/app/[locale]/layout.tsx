import type { Viewport } from "next";
import { NextIntlClientProvider } from "next-intl";
import { IBM_Plex_Sans_Arabic, Inter } from "next/font/google";
import { notFound } from "next/navigation";

import { SessionSync } from "@/features/auth/components/SessionSync";
import "../globals.css";

const LOCALES = ["en", "ar"] as const;

/**
 * سكريبت الـtheme الـinline (نمط Next الرسمي — preventing-flash-before-hydration):
 * بيحط كلاس .dark قبل أول paint من localStorage وإلا prefers-color-scheme.
 * لازم يفضل متطابق مع resolveStoredTheme() في ThemeToggle (نفس الترتيب) —
 * الـtry/catch عشان localStorage مش متاح (وضع خاص) نرجع للنظام.
 */
const THEME_SCRIPT = `(function(){var d=window.matchMedia("(prefers-color-scheme: dark)").matches;try{var t=localStorage.getItem("theme");if(t==="dark")d=true;else if(t==="light")d=false}catch(e){}document.documentElement.classList.toggle("dark",d)})()`;

/** theme-color = خلفية الصفحة في الوضعين (globals.css). */
export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f7f8fa" },
    { media: "(prefers-color-scheme: dark)", color: "#13181f" },
  ],
};

// الـlayout بيقرا الـlocale من الـparams (للـhtml lang/dir ورسايل next-intl) —
// blocking route مقصود: مفيش fallback shell هنا، صفحات الـapp كلها بتعتمد على
// الـlocale من أول paint.
export const instant = false;

/** [locale] قبل الـroot layout = root parameter — لازم يتحدد للـstatic generation. */
export function generateStaticParams() {
  return LOCALES.map((locale) => ({ locale }));
}

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const plexArabic = IBM_Plex_Sans_Arabic({
  variable: "--font-plex-arabic",
  subsets: ["arabic"],
  weight: ["400", "500", "600"],
});

/** layout الـ[locale] هو الـroot layout (النمط الرسمي للـi18n في Next 16). */
export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!LOCALES.includes(locale as (typeof LOCALES)[number])) {
    notFound();
  }
  const messages = (await import(`../../messages/${locale}.json`)).default;

  return (
    <html
      lang={locale}
      dir={locale === "ar" ? "rtl" : "ltr"}
      className={`${inter.variable} ${plexArabic.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="min-h-full bg-page font-sans text-foreground">
        <NextIntlClientProvider messages={messages} locale={locale}>
          {children}
          <SessionSync />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
