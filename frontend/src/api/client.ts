/** Thin fetch wrapper. The session lives in an httpOnly cookie, so there is no token handling here. */

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
  ) {
    super(message);
  }
}

type Method = "GET" | "POST" | "PATCH" | "DELETE";

export async function request<T = unknown>(method: Method, path: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method, credentials: "same-origin" };
  if (body instanceof FormData) {
    init.body = body; // browser sets the multipart boundary
  } else if (body !== undefined) {
    init.body = JSON.stringify(body);
    init.headers = { "content-type": "application/json" };
  }

  const resp = await fetch(`/api/v1${path}`, init);
  if (resp.status === 204) return undefined as T;
  const data = await resp.json().catch(() => null);
  if (!resp.ok) throw toError(resp.status, data);
  return data as T;
}

function toError(status: number, data: unknown): ApiError {
  const detail = (data as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return new ApiError(status, detail);
  if (Array.isArray(detail)) {
    const msg = detail
      .map((d: { loc?: unknown[]; msg?: string }) => `${d.loc?.at(-1) ?? "field"}: ${d.msg}`)
      .join("; ");
    return new ApiError(status, msg);
  }
  if (detail && typeof detail === "object" && "message" in detail) {
    const d = detail as { message: string; code?: string };
    return new ApiError(status, d.message, d.code);
  }
  return new ApiError(status, `Something went wrong (${status}). Please try again.`);
}
