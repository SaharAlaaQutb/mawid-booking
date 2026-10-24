export type ApiErrorBody = {
  code?: string;
  detail?: string;
  fields?: Record<string, string[]>;
  request_id?: string;
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields: Record<string, string[]>;
  readonly requestId?: string;

  constructor(message: string, status: number, body: ApiErrorBody = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code ?? "unknown_error";
    this.fields = body.fields ?? {};
    this.requestId = body.request_id;
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  headers?: HeadersInit;
  signal?: AbortSignal;
  token?: string | null;
};

function parseBody(text: string): ApiErrorBody | null {
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text) as ApiErrorBody;
  } catch {
    return null;
  }
}

export class ApiClient {
  private accessToken: string | null = null;

  constructor(private readonly baseUrl = "/api") {}

  setAccessToken(token: string | null): void {
    this.accessToken = token;
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { method = "GET", body, headers, signal, token } = options;
    const requestHeaders = new Headers(headers);

    if (body !== undefined && !(body instanceof FormData)) {
      requestHeaders.set("Content-Type", "application/json");
    }

    const authToken = token === undefined ? this.accessToken : token;
    if (authToken) {
      requestHeaders.set("Authorization", `Bearer ${authToken}`);
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers: requestHeaders,
      body: body === undefined || body instanceof FormData ? undefined : JSON.stringify(body),
      credentials: "include",
      signal,
    });

    if (response.status === 204) {
      return undefined as T;
    }

    const text = await response.text();
    const data = parseBody(text);

    if (!response.ok) {
      throw new ApiError(
        data?.detail ?? `Request failed with status ${response.status}`,
        response.status,
        data ?? {},
      );
    }

    return data as T;
  }

  get<T>(path: string, options: Omit<RequestOptions, "method" | "body"> = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: "GET" });
  }

  post<T>(path: string, body?: unknown, options: Omit<RequestOptions, "method"> = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: "POST", body });
  }

  patch<T>(path: string, body?: unknown, options: Omit<RequestOptions, "method"> = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: "PATCH", body });
  }

  delete<T>(path: string, options: Omit<RequestOptions, "method" | "body"> = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: "DELETE" });
  }
}

export const apiClient = new ApiClient();
