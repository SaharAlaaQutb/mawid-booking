import { useTranslation } from "react-i18next";
import { Home, LogOut } from "lucide-react";
import { Link, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "@/shared/auth/AuthProvider";
import { Button } from "@/shared/ui/Button";
import { LanguageSwitcher } from "@/shared/ui/LanguageSwitcher";

export function StaffLayout() {
  const { t } = useTranslation(["common", "staff"]);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/");
  }

  return (
    <div className="flex min-h-screen bg-bg">
      <aside className="hidden w-64 shrink-0 border-e border-border bg-surface p-4 lg:flex lg:flex-col">
        <Link to="/staff" className="text-xl font-bold text-primary">
          {t("common:appName")}
        </Link>
        <nav className="mt-6 space-y-1" aria-label={t("common:nav.staff")}>
          <Link
            to="/staff"
            className="flex min-h-11 items-center gap-2 rounded bg-primary/10 px-3 text-sm font-semibold text-primary"
          >
            <Home aria-hidden="true" className="h-4 w-4" />
            {t("staff:dashboard.title")}
          </Link>
        </nav>
        <div className="mt-auto space-y-3 border-t border-border pt-4">
          {user ? (
            <div>
              <p className="text-xs text-muted">{t("staff:dashboard.signedInAs")}</p>
              <p className="truncate text-sm font-semibold">{user.email}</p>
            </div>
          ) : null}
          <Button variant="ghost" size="sm" onClick={() => void handleLogout()}>
            <LogOut aria-hidden="true" className="h-4 w-4" />
            {t("common:actions.signOut")}
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-border bg-surface px-4 py-3 lg:px-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">
              {t("common:nav.staff")}
            </p>
            {user ? <p className="text-sm font-semibold">{user.email}</p> : null}
          </div>
          <LanguageSwitcher />
        </header>
        <main className="flex-1 p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
