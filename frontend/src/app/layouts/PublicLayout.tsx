import { useTranslation } from "react-i18next";
import { Link, Outlet } from "react-router-dom";

import { LanguageSwitcher } from "@/shared/ui/LanguageSwitcher";
import { buttonStyles } from "@/shared/ui/Button";

export function PublicLayout() {
  const { t } = useTranslation("common");

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Link to="/" className="text-xl font-bold tracking-tight text-primary">
            {t("appName")}
          </Link>
          <div className="flex items-center gap-2 sm:gap-4">
            <nav className="hidden items-center gap-1 sm:flex" aria-label={t("nav.book")}>
              <Link
                to="/book"
                className="rounded px-3 py-2 text-sm font-semibold text-muted hover:bg-bg hover:text-text"
              >
                {t("nav.book")}
              </Link>
              <Link to="/staff/login" className={buttonStyles("secondary", "sm")}>
                {t("nav.staff")}
              </Link>
            </nav>
            <LanguageSwitcher />
          </div>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-border bg-surface">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-2 px-4 py-6 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p>
            {t("appName")} — {t("tagline")}
          </p>
          <p>{t("footer.builtWith")}</p>
        </div>
      </footer>
    </div>
  );
}
