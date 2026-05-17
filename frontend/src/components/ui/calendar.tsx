"use client"

import * as React from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { DayPicker } from "react-day-picker"

import { cn } from "@/lib/utils"

export type CalendarProps = React.ComponentProps<typeof DayPicker>

function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  ...props
}: CalendarProps) {
  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      className={cn("p-4", className)}
      classNames={{
        /* react-day-picker v10 class names */
        months: "relative flex flex-col sm:flex-row gap-4",
        month: "w-full",
        month_caption: "flex justify-center pt-1 relative items-center mb-4",
        caption_label: "text-sm font-semibold text-foreground",
        nav: "flex items-center gap-1",
        button_previous: cn(
          "absolute left-1 top-1 inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors",
          "h-7 w-7 bg-transparent p-0 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        ),
        button_next: cn(
          "absolute right-1 top-1 inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors",
          "h-7 w-7 bg-transparent p-0 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        ),
        month_grid: "w-full border-collapse",
        weekdays: "flex",
        weekday: "text-muted-foreground rounded-md w-9 font-medium text-[0.8rem] text-center",
        week: "flex w-full mt-1",
        day: "h-9 w-9 text-center text-sm p-0 relative",
        day_button: cn(
          "inline-flex items-center justify-center rounded-md text-sm font-normal transition-colors",
          "h-9 w-9 p-0 hover:bg-accent hover:text-accent-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          "aria-selected:opacity-100"
        ),
        range_end: "day-range-end rounded-r-md",
        range_start: "day-range-start rounded-l-md",
        selected:
          "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground focus:bg-primary focus:text-primary-foreground rounded-md",
        today: "bg-accent text-accent-foreground rounded-md font-semibold",
        outside:
          "text-muted-foreground/40 aria-selected:bg-accent/50 aria-selected:text-muted-foreground",
        disabled: "text-muted-foreground opacity-50",
        range_middle:
          "aria-selected:bg-accent aria-selected:text-accent-foreground",
        hidden: "invisible",
        ...classNames,
      }}
      components={{
        Chevron: ({ orientation, ...chevronProps }) => {
          if (orientation === "left") {
            return <ChevronLeft className="h-4 w-4" />
          }
          return <ChevronRight className="h-4 w-4" />
        },
      }}
      {...props}
    />
  )
}
Calendar.displayName = "Calendar"

export { Calendar }
