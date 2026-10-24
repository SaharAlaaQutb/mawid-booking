import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "@/shared/auth/AuthProvider";
import { Skeleton } from "@/shared/ui/Skeleton";

export function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return (
      <div className="mx-auto w-full max-w-5xl p-6" aria-busy="true">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="mt-4 h-40 w-full" />
      </div>
    );
  }

  if (status === "anonymous") {
    return <Navigate to="/staff/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}
