import type { Locale } from "@/shared/i18n";

type DateInput = Date | string | number;

function toDate(value: DateInput): Date {
  return value instanceof Date ? value : new Date(value);
}

export function formatDate(
  value: DateInput,
  locale: Locale,
  options: Intl.DateTimeFormatOptions = {},
): string {
  return new Intl.DateTimeFormat(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
    ...options,
  }).format(toDate(value));
}

export function formatTime(
  value: DateInput,
  locale: Locale,
  options: Intl.DateTimeFormatOptions = {},
): string {
  return new Intl.DateTimeFormat(locale, {
    hour: "numeric",
    minute: "2-digit",
    ...options,
  }).format(toDate(value));
}

export function formatDateTime(
  value: DateInput,
  locale: Locale,
  options: Intl.DateTimeFormatOptions = {},
): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
    ...options,
  }).format(toDate(value));
}

export function formatCurrency(minorUnits: number, currency: string, locale: Locale): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
  }).format(minorUnits / 100);
}

export function formatNumber(value: number, locale: Locale): string {
  return new Intl.NumberFormat(locale).format(value);
}
