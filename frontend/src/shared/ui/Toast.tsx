import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react"

import { cn } from "@/shared/lib/cn"

const TOAST_DURATION = 4000

interface ToastItem {
  id: string
  title?: string
  description?: string
  action?: { label: string; onClick: () => void }
  duration?: number
}

const ToastContext = createContext<{
  toasts: ToastItem[]
  toast: (props: Omit<ToastItem, "id">) => string
  dismiss: (id: string) => void
} | null>(null)

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider")
  }
  return context
}

const timeoutRefs = new Map<string, ReturnType<typeof setTimeout>>()

function clearTimeoutFor(id: string) {
  const timeout = timeoutRefs.get(id)
  if (timeout) {
    clearTimeout(timeout)
    timeoutRefs.delete(id)
  }
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

      const dismiss = useCallback((id: string) => {
    clearTimeoutFor(id)
    setToasts((existing) => existing.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback(
    (props: Omit<ToastItem, "id">) => {
      const id = Math.random().toString(36).slice(2)
      setToasts((existing) => [...existing, { id, ...props }])
      const duration = props.duration ?? TOAST_DURATION
      const timeout = setTimeout(() => dismiss(id), duration)
      timeoutRefs.set(id, timeout)
      return id
    },
    [dismiss],
  )

  useEffect(() => {
    return () => {
      timeoutRefs.forEach((timeout, id) => {
        clearTimeout(timeout)
        timeoutRefs.delete(id)
      })
    }
  }, [])

  return (
    <ToastContext.Provider value={{ toasts, toast, dismiss }}>
      <div className="fixed top-0 right-0 p-4 z-50 flex flex-col gap-2 pointer-events-none">
        {children}
        {toasts.map((t) => (
          <div
            key={t.id}
            className={cn(
              "flex w-[380px] items-start gap-3 rounded border border-border bg-surface p-4 shadow-lg",
              "pointer-events-auto",
            )}
          >
            <div className="flex-1">
              {t.title && <ToastTitle>{t.title}</ToastTitle>}
              {t.description && <ToastDescription>{t.description}</ToastDescription>}
            </div>
            {t.action && (
              <ToastAction onClick={t.action.onClick}>{t.action.label}</ToastAction>
            )}
            <ToastClose onClick={() => dismiss(t.id)} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export const ToastViewport = ({
  className,
}: { className?: string }) => (
  <div className={cn("fixed top-0 right-0 p-4 z-50 flex flex-col gap-2 pointer-events-none", className)} />
)

export function ToastTitle({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("font-semibold", className)}>{children}</div>
}

export function ToastDescription({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("text-sm text-muted", className)}>{children}</div>
}

export function ToastAction({
  className,
  onClick,
  children,
}: {
  className?: string
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      className={cn(
        "inline-flex items-center rounded border border-transparent bg-transparent px-2 py-1 text-sm font-medium text-accent transition-colors hover:bg-accent/10 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 disabled:opacity-50",
        className,
      )}
      onClick={onClick}
    >
      {children}
    </button>
  )
}

export function ToastClose({
  className,
  onClick,
}: {
  className?: string
  onClick: () => void
}) {
  return (
      <button
        aria-label="Close"
        className={cn(
          "rounded inset-0 p-1 text-text opacity-50 transition-colors hover:opacity-75 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2",
          className,
        )}
        onClick={onClick}
      />
  )
}
