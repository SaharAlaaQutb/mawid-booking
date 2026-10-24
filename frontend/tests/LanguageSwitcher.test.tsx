import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { describe, expect, it } from "vitest";

import { LocaleProvider } from "@/shared/i18n/LocaleProvider";
import { LOCALE_STORAGE_KEY } from "@/shared/i18n";
import { LanguageSwitcher } from "@/shared/ui/LanguageSwitcher";

describe("LanguageSwitcher", () => {
  it("switches the document to Arabic RTL and persists the choice", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <LocaleProvider>
        <LanguageSwitcher />
      </LocaleProvider>,
    );

    await user.click(screen.getByRole("button", { name: /العربية/i }));

    await waitFor(() => {
      expect(document.documentElement.lang).toBe("ar");
      expect(document.documentElement.dir).toBe("rtl");
    });
    expect(window.localStorage.getItem(LOCALE_STORAGE_KEY)).toBe("ar");
    expect((await axe(container)).violations).toHaveLength(0);
  });

  it("marks the active language as pressed", async () => {
    const user = userEvent.setup();
    render(
      <LocaleProvider>
        <LanguageSwitcher />
      </LocaleProvider>,
    );

    expect(screen.getByRole("button", { name: /English/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    await user.click(screen.getByRole("button", { name: /العربية/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /العربية/i })).toHaveAttribute(
        "aria-pressed",
        "true",
      );
    });
  });
});
