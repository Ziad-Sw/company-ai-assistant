import { cn } from "@/lib/utils";

/**
 * أيقونات stroke صغيرة مشتركة (24×24) — الحجم بـprop صريح (sm 16 / md 24 /
 * lg 32) واللون من السياق (currentColor)، عشان مفيش تعارض classes في الحجم.
 */
const ICON_SIZES = { sm: "size-4", md: "size-6", lg: "size-8" } as const;

export type IconProps = {
  size?: keyof typeof ICON_SIZES;
  className?: string;
};

function iconClasses(size: keyof typeof ICON_SIZES, className = ""): string {
  return cn(ICON_SIZES[size], "shrink-0", className);
}

export function PlusIcon({ size = "sm", className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={iconClasses(size, className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

export function ChatBubbleIcon({ size = "sm", className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={iconClasses(size, className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path
        d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5c-1.2 0-2.4-.25-3.4-.7L4 20l.8-4.1A8.5 8.5 0 1 1 21 11.5Z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function LogOutIcon({ size = "sm", className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={iconClasses(size, className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" strokeLinecap="round" />
      <path d="M16 17l5-5-5-5m5 5H9" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function SunIcon({ size = "sm", className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={iconClasses(size, className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <circle cx="12" cy="12" r="5" />
      <path
        d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function MoonIcon({ size = "sm", className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={iconClasses(size, className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" strokeLinejoin="round" />
    </svg>
  );
}

/**
 * أيقونة طي/فتح الـsidebar (زي Gemini) — مربع مدور فيه panel ضيق على جهة
 * الـstart وسهم بينوّر ناحيته. في الـRTL بتنعكس بالكامل من الـcaller
 * (rtl:-scale-x-100) عشان السهم يفضل بينوّر على الـpanel.
 */
export function PanelToggleIcon({ size = "sm", className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={iconClasses(size, className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <rect x="3" y="4" width="18" height="16" rx="4" />
      <path d="M9.5 4v16" strokeLinecap="round" />
      <path d="M15 12h-3m0 0 2-2m-2 2 2 2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** أيقونات صفوف جدول المستندات (features/admin-documents) — كلها 16px شائعة. */

export function UploadIcon({ size = "sm", className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={iconClasses(size, className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M12 15V4m0 0 4 4m-4-4L8 8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" strokeLinecap="round" />
    </svg>
  );
}

export function RefreshIcon({ size = "sm", className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={iconClasses(size, className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path
        d="M20 11a8 8 0 1 0-2.3 6.3M20 12v-5m0 5h-5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function ClockIcon({ size = "sm", className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={iconClasses(size, className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function ListIcon({ size = "sm", className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={iconClasses(size, className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M8 6h12M8 12h12M8 18h12" strokeLinecap="round" />
      <path d="M4 6h.01M4 12h.01M4 18h.01" strokeLinecap="round" />
    </svg>
  );
}

export function PencilIcon({ size = "sm", className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={iconClasses(size, className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path
        d="m15 5 4 4M4 20l1-4L16.5 4.5a2.1 2.1 0 0 1 3 3L8 19l-4 1Z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function TrashIcon({ size = "sm", className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={iconClasses(size, className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path
        d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function UsersIcon({ size = "sm", className }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={iconClasses(size, className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      {/* Lucide "users" — شخصين (رأس + جسم) مع رأس ثانٍ جزئي. */}
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
