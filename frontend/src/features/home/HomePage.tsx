import { CalendarClock, Globe2, MailCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Badge } from "@/shared/ui/Badge";
import { buttonStyles } from "@/shared/ui/Button";

const featureKeys = ["availability", "reminders", "bilingual"] as const;
const featureIcons = [CalendarClock, MailCheck, Globe2];
const endpointSummaries = [
  "GET /health → 200",
  "POST /api/auth/token/ → 200",
  "GET /api/schema/ → 200",
];

export function HomePage() {
  const { t } = useTranslation("common");

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 lg:py-20">
      <section className="grid items-center gap-10 lg:grid-cols-[1.2fr_0.8fr]">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-primary">
            {t("home.eyebrow")}
          </p>
          <h1 className="mt-4 text-4xl font-bold leading-tight tracking-tight text-text sm:text-5xl">
            {t("home.title")}
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-muted">{t("home.description")}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/book" className={buttonStyles("primary", "lg")}>
              {t("home.primaryCta")}
            </Link>
            <Link to="/staff/login" className={buttonStyles("secondary", "lg")}>
              {t("home.secondaryCta")}
            </Link>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-surface p-6 shadow-card">
          <Badge tone="success">{t("foundation.badge")}</Badge>
          <h2 className="mt-4 text-xl font-bold">{t("foundation.title")}</h2>
          <p className="mt-2 text-sm leading-6 text-muted">{t("foundation.description")}</p>
          <div className="mt-6 space-y-3" dir="ltr">
            {endpointSummaries.map((summary) => (
              <div
                key={summary}
                className="flex items-center gap-3 rounded border border-border bg-bg px-3 py-2"
              >
                <span className="h-2.5 w-2.5 rounded-full bg-success" aria-hidden="true" />
                <code className="text-xs text-muted">{summary}</code>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mt-16 lg:mt-24">
        <h2 className="text-2xl font-bold tracking-tight">{t("home.featuresTitle")}</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {featureKeys.map((key, index) => {
            const Icon = featureIcons[index] ?? CalendarClock;
            return (
              <article key={key} className="rounded border border-border bg-surface p-6">
                <Icon aria-hidden="true" className="h-6 w-6 text-primary" />
                <h3 className="mt-4 text-lg font-semibold">{t(`home.features.${key}.title`)}</h3>
                <p className="mt-2 text-sm leading-6 text-muted">
                  {t(`home.features.${key}.description`)}
                </p>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}
