import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

import i18n from "@/shared/i18n";

afterEach(async () => {
  cleanup();
  window.localStorage.clear();
  document.documentElement.lang = "en";
  document.documentElement.dir = "ltr";
  await i18n.changeLanguage("en");
});
