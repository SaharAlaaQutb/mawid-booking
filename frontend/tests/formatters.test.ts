import { describe, expect, it } from "vitest";

import {
  formatCurrency,
  formatDate,
  formatDateTime,
  formatNumber,
  formatTime,
} from "@/shared/i18n/formatters";

const fixedDate = new Date("2026-10-26T09:30:00Z");

describe("locale formatters", () => {
  it("formats dates in English", () => {
    const value = formatDate(fixedDate, "en", { timeZone: "UTC" });

    expect(value).toContain("2026");
    expect(value).toContain("Oct");
  });

  it("formats dates in Arabic", () => {
    const value = formatDate(fixedDate, "ar", { timeZone: "UTC" });

    expect(value).not.toBe("");
    expect(value).not.toBe(formatDate(fixedDate, "en", { timeZone: "UTC" }));
  });

  it("formats times in both locales", () => {
    expect(formatTime(fixedDate, "en", { timeZone: "UTC" })).toContain("9:30");
    expect(formatTime(fixedDate, "ar", { timeZone: "UTC" })).not.toBe("");
  });

  it("formats date times and numbers", () => {
    expect(formatDateTime(fixedDate, "en", { timeZone: "UTC" })).toContain("2026");
    expect(formatNumber(1234, "en")).toBe("1,234");
  });

  it("formats minor currency units", () => {
    expect(formatCurrency(1250, "SAR", "en")).toContain("12.50");
  });
});
