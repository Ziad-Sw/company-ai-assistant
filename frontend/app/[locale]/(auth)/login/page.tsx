import { LanguageSwitcher } from "@/components/shared/LanguageSwitcher";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import { LoginForm } from "@/features/auth/components/LoginForm";
import { RedirectIfAuthed } from "@/features/auth/components/RedirectIfAuthed";

export default function LoginPage() {
  return (
    <main className="flex min-h-dvh flex-1 items-center justify-center px-4 py-12">
      <div className="fixed end-4 top-4 z-10 flex items-center gap-2">
        <ThemeToggle />
        <LanguageSwitcher />
      </div>
      <RedirectIfAuthed />
      <LoginForm />
    </main>
  );
}
