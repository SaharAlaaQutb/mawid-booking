import {
  Content as SelectContent,
  Group as SelectGroup,
  Item as SelectItem,
  Label as SelectLabel,
  Root as SelectRoot,
  ScrollDownButton as SelectScrollDownButton,
  ScrollUpButton as SelectScrollUpButton,
  Separator as SelectSeparator,
  Trigger as SelectTrigger,
  Value as SelectValue,
} from "@radix-ui/react-select"
import { cva, type VariantProps } from "class-variance-authority"
import { type ReactNode } from "react"

import { cn } from "@/shared/lib/cn"

const selectTrigger = cva(
  "inline-flex items-center justify-center rounded border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {
      size: {
        sm: "h-8 px-2 text-xs",
        md: "h-10 px-3 text-sm",
        lg: "h-11 px-3 text-base",
      },
    },
    defaultVariants: {
      size: "md",
    },
  },
)

const selectContent = cva(
  "rounded border border-border bg-surface text-text shadow-md focus-visible:outline-none",
  {
    variants: {
      size: {
        sm: "text-xs",
        md: "text-sm",
        lg: "text-base",
      },
    },
    defaultVariants: {
      size: "md",
    },
  },
)

const selectValue = cva("flex items-center gap-2 truncate", {
  variants: {
    size: {
      sm: "text-xs",
      md: "text-sm",
      lg: "text-base",
    },
  },
  defaultVariants: {
    size: "md",
  },
})

interface SelectProps {
  value?: string
  onValueChange?: (value: string) => void
  placeholder?: string
  name?: string
  required?: boolean
  disabled?: boolean
  size?: VariantProps<typeof selectTrigger>["size"]
  className?: string
  children: ReactNode
}

export function Select({
  className,
  value,
  onValueChange,
  placeholder,
  name,
  required,
  disabled,
  size = "md",
  children,
  ...props
}: SelectProps) {
  return (
    <SelectRoot
      value={value ?? ""}
      onValueChange={onValueChange}
      name={name}
      required={required}
      disabled={disabled}
      {...props}
    >
      <SelectTrigger className={cn(selectTrigger({ size }), className)}>
        <SelectValue placeholder={placeholder} className={selectValue({ size })} />
      </SelectTrigger>
      <SelectContent className={cn(selectContent({ size }))}>{children}</SelectContent>
    </SelectRoot>
  )
}

export { SelectGroup, SelectLabel, SelectItem, SelectSeparator, SelectScrollDownButton, SelectScrollUpButton }
