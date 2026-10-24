import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "@/shared/auth/AuthProvider";
import { Button } from "@/shared/ui/Button";
import { FormField } from "@/shared/ui/FormField";
import { Input } from "@/shared/ui/Input";
import { LanguageSwitcher } from "@/shared/ui/LanguageSwitcher";

type LocationState = {
  from?: string;
};

export function LoginPage() {
  const { t } = useTranslation(["staff", "common", "errors"]);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login({ email, password });
      const state = location.state as LocationState | null;
      navigate(state?.from ?? "/staff", { replace: true });
    } catch {
      setError(t("staff:login.error"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-bg">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <Link to="/" className="text-xl font-bold text-primary">
            {t("common:appName")}
          </Link>
          <LanguageSwitcher />
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <section className="w-full max-w-md rounded-lg border border-border bg-surface p-6 shadow-card sm:p-8">
          <h1 className="text-2xl font-bold tracking-tight">{t("staff:login.title")}</h1>
          <p className="mt-2 text-sm leading-6 text-muted">{t("staff:login.description")}</p>

          <form className="mt-6 space-y-4" onSubmit={(event) => void handleSubmit(event)}>
            <FormField label={t("staff:login.email")} htmlFor="email">
              <Input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </FormField>

            <FormField label={t("staff:login.password")} htmlFor="password">
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </FormField>

            {error ? (
              <p
                role="alert"
                className="rounded border border-danger/30 bg-danger/5 p-3 text-sm text-danger"
              >
                {error}
              </p>
            ) : null}

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? t("staff:login.submitting") : t("staff:login.submit")}
            </Button>
          </form>
        </section>
      </main>
    </div>
  );
}
