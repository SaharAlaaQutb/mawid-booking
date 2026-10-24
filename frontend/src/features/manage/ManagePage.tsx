import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { EmptyState } from "@/shared/ui/EmptyState";

export function ManagePage() {
  const { token } = useParams();
  const { t } = useTranslation("staff");

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6 lg:py-16">
      <h1 className="text-3xl font-bold tracking-tight">{t("manage.title")}</h1>
      <p className="mt-3 text-base leading-7 text-muted">{t("manage.description")}</p>
      <div className="mt-8">
        <EmptyState
          title={t("manage.tokenLabel")}
          description={token ? <span dir="ltr">{token}</span> : undefined}
        />
      </div>
    </div>
  );
}
