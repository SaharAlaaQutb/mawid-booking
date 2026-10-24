import { Route, Routes } from "react-router-dom";

import { PublicLayout } from "@/app/layouts/PublicLayout";
import { StaffLayout } from "@/app/layouts/StaffLayout";
import { LoginPage } from "@/features/auth/LoginPage";
import { BookingPage } from "@/features/booking/BookingPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { HomePage } from "@/features/home/HomePage";
import { ManagePage } from "@/features/manage/ManagePage";
import { NotFoundPage } from "@/features/not-found/NotFoundPage";
import { RequireAuth } from "@/shared/auth/RequireAuth";

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route index element={<HomePage />} />
        <Route path="book" element={<BookingPage />} />
        <Route path="manage/:token" element={<ManagePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>

      <Route path="/staff/login" element={<LoginPage />} />

      <Route element={<RequireAuth />}>
        <Route path="/staff" element={<StaffLayout />}>
          <Route index element={<DashboardPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
