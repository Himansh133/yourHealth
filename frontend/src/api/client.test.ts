import { describe, expect, it, vi } from "vitest";
import { ApiError, request } from "./client";

function mockFetch(status: number, body?: unknown) {
  return vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    }),
  );
}

async function failure(p: Promise<unknown>): Promise<ApiError> {
  try {
    await p;
  } catch (e) {
    return e as ApiError;
  }
  throw new Error("expected the request to fail");
}

describe("request", () => {
  it("prefixes /api/v1, sends cookies and parses JSON", async () => {
    const fetch = mockFetch(200, { id: "1" });

    const data = await request<{ id: string }>("GET", "/profiles");

    expect(data).toEqual({ id: "1" });
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe("/api/v1/profiles");
    expect(init?.credentials).toBe("same-origin");
  });

  it("sends JSON bodies with content-type", async () => {
    const fetch = mockFetch(201, { id: "1" });
    await request("POST", "/profiles", { display_name: "Papa" });
    const init = fetch.mock.calls[0][1]!;
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ display_name: "Papa" }));
    expect(new Headers(init.headers).get("content-type")).toBe("application/json");
  });

  it("sends FormData as-is so the browser sets the multipart boundary", async () => {
    const fetch = mockFetch(201, { id: "1" });
    const form = new FormData();
    await request("POST", "/profiles/p/documents", form);
    const init = fetch.mock.calls[0][1]!;
    expect(init.body).toBe(form);
    expect(new Headers(init.headers).has("content-type")).toBe(false);
  });

  it("returns undefined for 204", async () => {
    mockFetch(204);
    expect(await request("DELETE", "/documents/d")).toBeUndefined();
  });

  it("throws ApiError with a string detail", async () => {
    mockFetch(401, { detail: "Wrong email or password" });
    await expect(request("POST", "/auth/login", {})).rejects.toEqual(
      new ApiError(401, "Wrong email or password"),
    );
  });

  it("uses message and code from a structured detail", async () => {
    mockFetch(422, { detail: { code: "pdf_encrypted", message: "This PDF is password-protected." } });
    const err = await failure(request("POST", "/x", {}));
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(422);
    expect(err.code).toBe("pdf_encrypted");
    expect(err.message).toBe("This PDF is password-protected.");
  });

  it("joins FastAPI validation errors into one readable message", async () => {
    mockFetch(422, {
      detail: [
        { loc: ["body", "password"], msg: "String should have at least 10 characters" },
        { loc: ["body", "email"], msg: "value is not a valid email address" },
      ],
    });
    const err = await failure(request("POST", "/auth/register", {}));
    expect(err.message).toBe(
      "password: String should have at least 10 characters; email: value is not a valid email address",
    );
  });

  it("gives a generic message when the server sends no JSON", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("Bad Gateway", { status: 502 }));
    const err = await failure(request("GET", "/profiles"));
    expect(err).toEqual(new ApiError(502, "Something went wrong (502). Please try again."));
  });
});
