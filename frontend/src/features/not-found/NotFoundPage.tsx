import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { buttonStyles } from "@/shared/ui/Button";

export function NotFoundPage() {
  const { t } = useTranslation("common");

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col items-start px-4 py-20 sm:px-6">
      <p className="text-sm font-semibold uppercase tracking-wide text-primary">404</p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight">{t("notFound.title")}</h1>
      <p className="mt-3 text-base text-muted">{t("notFound.description")}</p>
      <Link to="/" className={buttonStyles("primary", "md", "mt-6")}>
        {t("actions.backHome")}
      </Link>
    </div>
  );
}
