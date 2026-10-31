import {
  Content as TabsContentPrimitive,
  List as TabsListPrimitive,
  Root as TabsRootPrimitive,
  Trigger as TabsTriggerPrimitive,
} from "@radix-ui/react-tabs"
import { cva } from "class-variance-authority"
import { type ComponentPropsWithoutRef } from "react"

import { cn } from "@/shared/lib/cn"

const tabsList = cva("inline-flex h-10 items-center justify-center gap-1")

const tabsTrigger = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 data-[state=active]:bg-accent data-[state=active]:text-accent-foreground",
)

const tabsContent = cva("rounded border border-border bg-surface p-4")

export function Tabs({ className, ...props }: ComponentPropsWithoutRef<typeof TabsRootPrimitive> & { className?: string }) {
  return <TabsRootPrimitive className={cn("w-full", className)} {...props} />
}

export function TabsList(
  { className, ...props }: ComponentPropsWithoutRef<typeof TabsListPrimitive> & { className?: string },
) {
  return <TabsListPrimitive className={cn(tabsList(), className)} {...props} />
}

export function TabsTrigger(
  { className, ...props }: ComponentPropsWithoutRef<typeof TabsTriggerPrimitive> & { className?: string },
) {
  return <TabsTriggerPrimitive className={cn(tabsTrigger(), className)} {...props} />
}

export function TabsContent(
  { className, ...props }: ComponentPropsWithoutRef<typeof TabsContentPrimitive> & { className?: string },
) {
  return <TabsContentPrimitive className={cn(tabsContent(), className)} {...props} />
}
