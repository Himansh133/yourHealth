import { vi } from "vitest";

type Handler = unknown | ((body: unknown) => unknown);
type Route = { status?: number; body?: Handler };

/**
 * Fake backend for component tests: routes are "METHOD /path" (path without /api/v1, query ignored).
 * A route value can be a plain body (200) or {status, body}. Unknown routes return 404.
 */
export function mockApi(routes: Record<string, unknown>) {
  const calls: { method: string; path: string; body: unknown }[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const method = init?.method ?? "GET";
    const path = String(input).replace(/^\/api\/v1/, "").split("?")[0];
    const body = typeof init?.body === "string" ? JSON.parse(init.body) : init?.body;
    calls.push({ method, path, body });

    const route = routes[`${method} ${path}`];
    if (route === undefined) return json(404, { detail: "Not found" });
    const { status = 200, body: out } = isRoute(route) ? route : { body: route };
    const value = typeof out === "function" ? out(body) : out;
    return status === 204 ? new Response(null, { status }) : json(status, value);
  });
  return calls;
}

/** {status, body} wrapper only: a plain body may have its own "status" field (documents do). */
function isRoute(r: unknown): r is Route {
  if (typeof r !== "object" || r === null || Array.isArray(r)) return false;
  const keys = Object.keys(r);
  return typeof (r as Route).status === "number" && keys.every((k) => k === "status" || k === "body");
}

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}
