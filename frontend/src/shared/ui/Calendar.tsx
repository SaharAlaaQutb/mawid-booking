import {
  eachDayOfInterval,
  endOfMonth,
  format,
  isSameDay,
  isToday,
  startOfMonth,
} from "date-fns"

import { SlotButton } from "@/shared/ui/SlotButton"
import { cn } from "@/shared/lib/cn"

interface CalendarProps {
  selected?: Date
  month?: Date
  onSelect?: (date: Date) => void
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

export function Calendar({ selected, month = new Date(), onSelect }: CalendarProps) {
  const start = startOfMonth(month)
  const end = endOfMonth(month)
  const days = eachDayOfInterval({ start, end })

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm text-muted font-semibold">
        {WEEKDAYS.map((day) => (
          <span key={day} className="text-center w-8">
            {day}
          </span>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {days.map((day) => {
          const selectedDay = selected ? isSameDay(day, selected) : false
          return (
            <SlotButton
              key={day.toISOString()}
              variant={selectedDay ? "selected" : "available"}
              size="sm"
              onClick={() => onSelect?.(day)}
              className={cn("text-center w-8 h-8", isToday(day) && "ring-1 ring-inset ring-accent")}
              aria-label={format(day, "yyyy-MM-dd")}
              aria-pressed={selectedDay}
            >
              {format(day, "d")}
            </SlotButton>
          )
        })}
      </div>
    </div>
  )
}
