import { Languages } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useLocale } from "@/shared/i18n/LocaleProvider";
import type { Locale } from "@/shared/i18n";
import { cn } from "@/shared/lib/cn";

const options: Locale[] = ["en", "ar"];

export function LanguageSwitcher({ className }: { className?: string }) {
  const { t } = useTranslation("common");
  const { locale, setLocale } = useLocale();

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1 rounded-full border border-border bg-surface p-1",
        className,
      )}
      role="group"
      aria-label={t("language.label")}
    >
      <Languages aria-hidden="true" className="mx-1 h-4 w-4 text-muted" />
      {options.map((option) => {
        const active = locale === option;
        return (
          <button
            key={option}
            type="button"
            lang={option}
            aria-pressed={active}
            onClick={() => void setLocale(option)}
            className={cn(
              "min-h-9 rounded-full px-3 text-sm font-semibold transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2",
              active ? "bg-primary text-white" : "text-muted hover:bg-bg hover:text-text",
            )}
          >
            {t(`language.${option}`)}
          </button>
        );
      })}
    </div>
  );
}
