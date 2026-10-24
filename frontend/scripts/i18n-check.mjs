import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const localesDir = path.resolve("src/shared/i18n/locales");
const referenceLocale = "en";

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function flattenKeys(value, prefix = "") {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return [prefix];
  }

  return Object.entries(value).flatMap(([key, child]) => {
    const nextPrefix = prefix ? `${prefix}.${key}` : key;
    return flattenKeys(child, nextPrefix);
  });
}

function loadNamespace(locale, namespace) {
  const filePath = path.join(localesDir, locale, `${namespace}.json`);
  return new Set(flattenKeys(readJson(filePath)));
}

const locales = fs
  .readdirSync(localesDir, { withFileTypes: true })
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name);

if (!locales.includes(referenceLocale)) {
  console.error(`Missing reference locale: ${referenceLocale}`);
  process.exit(1);
}

const namespaces = fs
  .readdirSync(path.join(localesDir, referenceLocale))
  .filter((file) => file.endsWith(".json"))
  .map((file) => file.replace(/\.json$/, ""));

let hasErrors = false;

for (const namespace of namespaces) {
  const referenceKeys = loadNamespace(referenceLocale, namespace);

  for (const locale of locales.filter((value) => value !== referenceLocale)) {
    const localePath = path.join(localesDir, locale, `${namespace}.json`);
    if (!fs.existsSync(localePath)) {
      console.error(`[${namespace}] missing file for locale "${locale}"`);
      hasErrors = true;
      continue;
    }

    const localeKeys = loadNamespace(locale, namespace);
    const missing = [...referenceKeys].filter((key) => !localeKeys.has(key));
    const extra = [...localeKeys].filter((key) => !referenceKeys.has(key));

    for (const key of missing) {
      console.error(`[${namespace}] ${locale} is missing "${key}"`);
      hasErrors = true;
    }
    for (const key of extra) {
      console.error(`[${namespace}] ${locale} has extra "${key}"`);
      hasErrors = true;
    }
  }
}

if (hasErrors) {
  process.exit(1);
}

console.log(
  `i18n check passed for ${namespaces.length} namespace(s) and ${locales.length} locale(s).`,
);
