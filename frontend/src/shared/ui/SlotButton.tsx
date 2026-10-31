import { cva, type VariantProps } from "class-variance-authority"
import { forwardRef } from "react"

import { cn } from "@/shared/lib/cn"

const slotButtonVariants = cva(
  "inline-flex items-center justify-center rounded text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        available: "bg-surface text-text border border-border hover:bg-bg",
        selected: "bg-primary text-white",
        unavailable: "border border-border bg-surface text-muted",
        taken: "border border-dashed border-border bg-surface text-muted",
      },
      size: {
        sm: "h-8 px-2",
        md: "h-10 px-3",
        lg: "h-12 px-4",
      },
    },
    defaultVariants: {
      variant: "available",
      size: "md",
    },
  },
)

export interface SlotButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: VariantProps<typeof slotButtonVariants>["variant"]
  size?: VariantProps<typeof slotButtonVariants>["size"]
}

export const SlotButton = forwardRef<HTMLButtonElement, SlotButtonProps>(
  ({ className, variant = "available", size = "md", disabled, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(slotButtonVariants({ variant, size }), className)}
      disabled={disabled}
      {...props}
    />
  ),
)

SlotButton.displayName = "SlotButton"
