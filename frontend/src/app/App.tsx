import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

import { AppRoutes } from "@/app/router";
import { ApiProvider } from "@/shared/api/ApiProvider";
import { AuthProvider } from "@/shared/auth/AuthProvider";
import { LocaleProvider } from "@/shared/i18n/LocaleProvider";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

export function App() {
  return (
    <LocaleProvider>
      <ApiProvider>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <BrowserRouter>
              <AppRoutes />
            </BrowserRouter>
          </AuthProvider>
        </QueryClientProvider>
      </ApiProvider>
    </LocaleProvider>
  );
}
