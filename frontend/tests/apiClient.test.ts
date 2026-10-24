import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiClient, ApiError } from "@/shared/api/client";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("ApiClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ status: "ok" }));
    vi.stubGlobal("fetch", fetchMock);

    const client = new ApiClient();
    const result = await client.get<{ status: string }>("/health");

    expect(result).toEqual({ status: "ok" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/health",
      expect.objectContaining({ method: "GET", credentials: "include" }),
    );
  });

  it("sends the access token", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: "1" }));
    vi.stubGlobal("fetch", fetchMock);

    const client = new ApiClient();
    client.setAccessToken("access-token");
    await client.get("/auth/me/");

    const request = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const headers = request.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer access-token");
  });

  it("maps error envelopes to ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            code: "slot_taken",
            detail: "This slot is no longer available.",
            fields: { start: ["Taken"] },
            request_id: "request-1",
          },
          409,
        ),
      ),
    );

    const client = new ApiClient();

    const error = await client.post("/appointments/", {}).catch((cause: unknown) => cause);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 409,
      code: "slot_taken",
      fields: { start: ["Taken"] },
      requestId: "request-1",
    });
  });

  it("returns undefined for 204 responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));

    const client = new ApiClient();

    await expect(client.delete("/auth/logout/")).resolves.toBeUndefined();
  });
});
