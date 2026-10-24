import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";

import { Button } from "@/shared/ui/Button";

describe("Button", () => {
  it("calls the click handler", async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();

    render(<Button onClick={handleClick}>Continue</Button>);
    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(handleClick).toHaveBeenCalledOnce();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<Button>Continue</Button>);

    expect((await axe(container)).violations).toHaveLength(0);
  });
});
