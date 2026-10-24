import "@fontsource/cairo/400.css";
import "@fontsource/cairo/600.css";
import "@fontsource/cairo/700.css";
import "@fontsource/inter/400.css";
import "@fontsource/inter/600.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "@/shared/i18n";
import { App } from "@/app/App";
import "@/app/styles.css";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element not found");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
