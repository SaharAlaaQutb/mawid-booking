import {
  Close as DialogClosePrimitive,
  Content as DialogContentPrimitive,
  Description as DialogDescriptionPrimitive,
  Root as DialogRootPrimitive,
  Title as DialogTitlePrimitive,
  Trigger as DialogTriggerPrimitive,
} from "@radix-ui/react-dialog"
import { type ComponentPropsWithoutRef } from "react"

import { cn } from "@/shared/lib/cn"

export const Dialog = DialogRootPrimitive

export function DialogTrigger(
  { className, ...props }: ComponentPropsWithoutRef<typeof DialogTriggerPrimitive>,
) {
  return (
    <DialogTriggerPrimitive
      className={cn("inline-flex items-center justify-center rounded text-sm font-medium transition-colors", className)}
      {...props}
    />
  )
}

export function DialogContent(
  { className, ...props }: ComponentPropsWithoutRef<typeof DialogContentPrimitive> & { className?: string },
) {
  return (
    <DialogContentPrimitive
      className={cn("rounded-lg border border-border bg-surface p-6 shadow-lg", className)}
      {...props}
    />
  )
}

export function DialogTitle(
  { className, ...props }: ComponentPropsWithoutRef<typeof DialogTitlePrimitive>,
) {
  return <DialogTitlePrimitive className={cn("text-lg font-semibold", className)} {...props} />
}

export function DialogDescription(
  { className, ...props }: ComponentPropsWithoutRef<typeof DialogDescriptionPrimitive>,
) {
  return <DialogDescriptionPrimitive className={cn("text-sm text-muted", className)} {...props} />
}

export function DialogClose({ className, ...props }: ComponentPropsWithoutRef<typeof DialogClosePrimitive> & { className?: string }) {
  return (
    <DialogClosePrimitive
      aria-label="Close"
      className={cn("rounded inset-0 p-1 text-text opacity-50 transition-colors hover:opacity-75 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2", className)}
      {...props}
    />
  )
}
