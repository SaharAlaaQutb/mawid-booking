import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { buttonStyles } from "@/shared/ui/Button";
import { EmptyState } from "@/shared/ui/EmptyState";

export function BookingPage() {
  const { t } = useTranslation("booking");

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6 lg:py-16">
      <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
      <p className="mt-3 text-base leading-7 text-muted">{t("description")}</p>
      <div className="mt-8">
        <EmptyState
          title={t("placeholder")}
          action={
            <Link to="/" className={buttonStyles("secondary")}>
              {t("common:actions.backHome", { ns: "common" })}
            </Link>
          }
        />
      </div>
    </div>
  );
}
