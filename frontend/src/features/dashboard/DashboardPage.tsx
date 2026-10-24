import { useTranslation } from "react-i18next";

import { useAuth } from "@/shared/auth/AuthProvider";
import { Badge } from "@/shared/ui/Badge";
import { EmptyState } from "@/shared/ui/EmptyState";

export function DashboardPage() {
  const { t } = useTranslation(["staff", "calendar"]);
  const { user } = useAuth();

  return (
    <div className="mx-auto w-full max-w-5xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-primary">
            {t("staff:dashboard.title")}
          </p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight">
            {t("staff:dashboard.welcome")}
            {user?.full_name ? `, ${user.full_name}` : ""}
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
            {t("staff:dashboard.description")}
          </p>
        </div>
        <Badge tone="warning">{user?.role ?? ""}</Badge>
      </div>

      <div className="mt-8">
        <EmptyState title={t("calendar:title")} description={t("calendar:empty")} />
      </div>
    </div>
  );
}
