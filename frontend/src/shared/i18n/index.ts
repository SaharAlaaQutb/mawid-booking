import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import arBooking from "./locales/ar/booking.json";
import arCalendar from "./locales/ar/calendar.json";
import arCommon from "./locales/ar/common.json";
import arErrors from "./locales/ar/errors.json";
import arStaff from "./locales/ar/staff.json";
import enBooking from "./locales/en/booking.json";
import enCalendar from "./locales/en/calendar.json";
import enCommon from "./locales/en/common.json";
import enErrors from "./locales/en/errors.json";
import enStaff from "./locales/en/staff.json";

export const SUPPORTED_LOCALES = ["en", "ar"] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];

export const LOCALE_STORAGE_KEY = "mawid.locale";

export function toLocale(value: string | undefined): Locale {
  return value?.toLowerCase().startsWith("ar") ? "ar" : "en";
}

export function directionFor(locale: Locale): "ltr" | "rtl" {
  return locale === "ar" ? "rtl" : "ltr";
}

const resources = {
  en: {
    common: enCommon,
    booking: enBooking,
    calendar: enCalendar,
    staff: enStaff,
    errors: enErrors,
  },
  ar: {
    common: arCommon,
    booking: arBooking,
    calendar: arCalendar,
    staff: arStaff,
    errors: arErrors,
  },
};

if (!i18n.isInitialized) {
  void i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
      resources,
      fallbackLng: "en",
      supportedLngs: SUPPORTED_LOCALES,
      nonExplicitSupportedLngs: true,
      defaultNS: "common",
      ns: ["common", "booking", "calendar", "staff", "errors"],
      interpolation: {
        escapeValue: false,
      },
      detection: {
        order: ["querystring", "localStorage", "navigator"],
        lookupQuerystring: "lang",
        lookupLocalStorage: LOCALE_STORAGE_KEY,
        caches: ["localStorage"],
      },
    });
}

export default i18n;
