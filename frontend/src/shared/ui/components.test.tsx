import { fireEvent, render, screen } from "@testing-library/react"
import { userEvent } from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

afterEach(() => {
  document.body.innerHTML = ""
})

import { Calendar } from "@/shared/ui/Calendar"
import { Dialog, DialogClose, DialogContent, DialogTitle, DialogTrigger } from "@/shared/ui/Dialog"
import { Select, SelectItem } from "@/shared/ui/Select"
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/shared/ui/Sheet"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/Tabs"
import { ToastProvider, useToast } from "@/shared/ui/Toast"

describe("Select", () => {
  it("opens and selects an option", () => {
    const onValueChange = vi.fn()
    render(
      <Select value="" onValueChange={onValueChange} placeholder="Choose a service">
        <SelectItem value="consultation">Consultation</SelectItem>
        <SelectItem value="follow-up">Follow-up</SelectItem>
      </Select>,
    )

    fireEvent.click(screen.getByRole("combobox"))
    fireEvent.click(screen.getByRole("option", { name: "Consultation" }))

    expect(onValueChange).toHaveBeenCalledWith("consultation")
  })
})

describe("Dialog", () => {
  it("opens and closes", () => {
    function Example() {
      return (
        <Dialog>
          <DialogTrigger>Cancel appointment</DialogTrigger>
          <DialogContent>
            <DialogTitle>Confirm cancellation</DialogTitle>
            <DialogClose />
          </DialogContent>
        </Dialog>
      )
    }
    render(<Example />)

    fireEvent.click(screen.getByRole("button", { name: "Cancel appointment" }))
    expect(screen.getByText("Confirm cancellation")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /close/i }))
    expect(screen.queryByText("Confirm cancellation")).not.toBeInTheDocument()
  })
})

describe("Sheet", () => {
  it("renders sheet content", () => {
    function Example() {
      return (
        <Sheet>
          <SheetTrigger>Open sheet</SheetTrigger>
          <SheetContent>
            <SheetTitle>Sheet title</SheetTitle>
          </SheetContent>
        </Sheet>
      )
    }
    render(<Example />)
    fireEvent.click(screen.getByRole("button", { name: "Open sheet" }))
    expect(screen.getByText("Sheet title")).toBeInTheDocument()
  })
})

describe("Tabs", () => {
  it("activates a tab panel", async () => {
    function Example() {
      return (
        <Tabs defaultValue="a">
          <TabsList>
            <TabsTrigger value="a">First</TabsTrigger>
            <TabsTrigger value="b">Second</TabsTrigger>
          </TabsList>
          <TabsContent value="a">First content</TabsContent>
          <TabsContent value="b">Second content</TabsContent>
        </Tabs>
      )
    }
    render(<Example />)

    const onValueChange = vi.fn()
    const { container } = render(
      <Tabs value="a" onValueChange={onValueChange}>
        <TabsList>
          <TabsTrigger value="a">First</TabsTrigger>
          <TabsTrigger value="b">Second</TabsTrigger>
        </TabsList>
        <TabsContent value="a">First content</TabsContent>
        <TabsContent value="b">Second content</TabsContent>
      </Tabs>
    )

    const secondTrigger = Array.from(container.querySelectorAll("button")).find(
      (button) => button.textContent === "Second"
    )
    expect(secondTrigger).toBeTruthy()
    await userEvent.click(secondTrigger!)
    expect(onValueChange).toHaveBeenCalledWith("b")
  })
})

describe("Toast", () => {
  it("shows and dismisses a toast", () => {
    function ConfirmButton() {
      const { toast } = useToast()
      return (
        <button onClick={() => toast({ title: "Booking confirmed", description: "See you soon" })}>
          Confirm
        </button>
      )
    }
    function Example() {
      return (
        <ToastProvider>
          <ConfirmButton />
        </ToastProvider>
      )
    }
    render(<Example />)

    fireEvent.click(screen.getByRole("button", { name: "Confirm" }))
    expect(screen.getByText("Booking confirmed")).toBeInTheDocument()
    expect(screen.getByText("See you soon")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /close/i }))
    expect(screen.queryByText("Booking confirmed")).not.toBeInTheDocument()
  })
})

describe("Calendar", () => {
  it("renders month days and selects a date", () => {
    const onSelect = vi.fn()
    const selected = new Date(2026, 10, 2)
    render(<Calendar selected={selected} month={new Date(2026, 10, 1)} onSelect={onSelect} />)

    expect(screen.getByText("2")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /2026-11-03/ }))
    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(new Date(onSelect.mock.calls[0]![0] as Date).getDate()).toBe(3)
  })
})
