import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import i18n, { directionFor, LOCALE_STORAGE_KEY, type Locale, toLocale } from "@/shared/i18n";

type LocaleContextValue = {
  locale: Locale;
  direction: "ltr" | "rtl";
  setLocale: (locale: Locale) => Promise<void>;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

function applyDocumentLocale(locale: Locale): void {
  const direction = directionFor(locale);
  document.documentElement.lang = locale;
  document.documentElement.dir = direction;
}

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() =>
    toLocale(i18n.resolvedLanguage ?? i18n.language),
  );

  useEffect(() => {
    applyDocumentLocale(locale);
  }, [locale]);

  useEffect(() => {
    const handleLanguageChanged = (language: string) => {
      setLocaleState(toLocale(language));
    };

    i18n.on("languageChanged", handleLanguageChanged);
    return () => {
      i18n.off("languageChanged", handleLanguageChanged);
    };
  }, []);

  const setLocale = useCallback(async (nextLocale: Locale) => {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, nextLocale);
    await i18n.changeLanguage(nextLocale);
  }, []);

  const value = useMemo(
    () => ({
      locale,
      direction: directionFor(locale),
      setLocale,
    }),
    [locale, setLocale],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const context = useContext(LocaleContext);
  if (!context) {
    throw new Error("useLocale must be used inside LocaleProvider");
  }
  return context;
}
