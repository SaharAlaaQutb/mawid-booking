import { createContext, useContext } from "react";

import { apiClient, type ApiClient } from "@/shared/api/client";

const ApiContext = createContext<ApiClient>(apiClient);

export function ApiProvider({
  client = apiClient,
  children,
}: {
  client?: ApiClient;
  children: React.ReactNode;
}) {
  return <ApiContext.Provider value={client}>{children}</ApiContext.Provider>;
}

export function useApi(): ApiClient {
  return useContext(ApiContext);
}
