"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

import { supabase } from "../api/supabase";

type LoginErrorKey = "invalidCredentials" | "emailNotConfirmed" | "tooManyAttempts" | "network" | "generic";

/**
 * بيرجّع مفتاح رسالة الخطأ المناسبة من كود/رسالة Supabase — أماكن محددة
 * ومعروفة بس، ومفيش fallback عام بيكسر (كل الحالات ليها نص محدد).
 */
function resolveLoginErrorKey(error: { code?: string; message?: string }): LoginErrorKey {
  if (error.code === "invalid_credentials" || error.code === "user_not_found") return "invalidCredentials";
  if (error.code === "email_not_confirmed") return "emailNotConfirmed";
  if (error.code === "over_request_rate_limit" || error.code === "over_email_send_rate_limit") {
    return "tooManyAttempts";
  }
  if (error.message?.includes("fetch") || error.message?.includes("network")) return "network";
  return "generic";
}

export function LoginForm() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("auth");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorKey, setErrorKey] = useState<LoginErrorKey | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorKey(null);
    setIsSubmitting(true);
    try {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) {
        setErrorKey(resolveLoginErrorKey(error));
        return;
      }
      // الـroute guard في /(chat) بيعمل sync الجلسة — navigation من غير refresh
      // ممكن يوصل قبل الـstore يتحدّث، فبنعمل refresh كامل.
      router.replace(`/${locale}/chat`);
      router.refresh();
    } catch {
      setErrorKey("network");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex w-full max-w-sm flex-col gap-6 rounded-[var(--radius-lg)] border border-border bg-surface p-6">
      <div className="flex flex-col gap-1">
        <p className="text-sm font-medium text-primary" translate="no">
          Reel Estate
        </p>
        <h1 className="text-xl font-semibold text-foreground">{t("title")}</h1>
        <p className="text-sm text-muted">{t("subtitle")}</p>
      </div>

      <form onSubmit={handleSubmit} className="flex w-full flex-col gap-4" noValidate>
        {errorKey ? (
          <p
            role="alert"
            className="rounded-[var(--radius-sm)] bg-error-subtle px-3 py-2 text-sm text-error"
          >
            {t(`errors.${errorKey}`)}
          </p>
        ) : null}

        <div className="flex flex-col gap-1.5">
          <label htmlFor="login-email" className="text-sm font-medium text-foreground">
            {t("email")}
          </label>
          <Input
            id="login-email"
            name="email"
            type="email"
            autoComplete="email"
            spellCheck={false}
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={isSubmitting}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="login-password" className="text-sm font-medium text-foreground">
            {t("password")}
          </label>
          <Input
            id="login-password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={isSubmitting}
          />
        </div>

        <Button type="submit" size="lg" loading={isSubmitting} className="w-full">
          {isSubmitting ? t("submitting") : t("submit")}
        </Button>
      </form>
    </div>
  );
}
