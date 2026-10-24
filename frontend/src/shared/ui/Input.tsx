import { forwardRef, type InputHTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

export type InputProps = InputHTMLAttributes<HTMLInputElement>;

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        "min-h-11 w-full rounded border border-border bg-surface px-3 py-2 text-base text-text",
        "placeholder:text-muted focus-visible:border-accent focus-visible:outline-none",
        "focus-visible:ring-2 focus-visible:ring-accent/40 disabled:opacity-50",
        "aria-[invalid=true]:border-danger aria-[invalid=true]:ring-danger/30",
        className,
      )}
      {...props}
    />
  ),
);

Input.displayName = "Input";
