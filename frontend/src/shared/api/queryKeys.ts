export const queryKeys = {
  business: () => ["business"] as const,
  services: () => ["services"] as const,
  staff: (serviceId?: string) => ["staff", serviceId ?? "all"] as const,
  availability: (serviceId: string, staffId: string, date: string) =>
    ["availability", serviceId, staffId, date] as const,
  appointment: (token: string) => ["appointment", token] as const,
  calendar: (from: string, to: string, staffId?: string) =>
    ["calendar", from, to, staffId ?? "all"] as const,
  me: () => ["me"] as const,
};
