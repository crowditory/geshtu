import { browser } from "$app/environment";
import { getToken } from "$lib/stores/auth";

import type {
  Decision,
  DigestOut,
  Health,
  IssuedToken,
  Project,
  SearchOut,
  Token,
  User,
  UserWithToken,
} from "./types";

/**
 * API base URL.
 *
 * In production the admin SPA is served from the same origin as the
 * memory-api (Caddy routes `/api/*` to the api container, everything else
 * to admin), so a relative `/api` prefix Just Works. The build can be
 * overridden at build-time with `VITE_GESHTU_API_URL=https://...` if you
 * want to host the SPA somewhere else.
 */
const API_BASE: string =
  (import.meta.env.VITE_GESHTU_API_URL as string | undefined) ?? "/api";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown, message: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  query?: Record<string, string | number | boolean | undefined | null>,
  tokenOverride?: string,
): Promise<T> {
  if (!browser) {
    // Pages are CSR-only. If something tries to call this during SSR
    // (shouldn't happen with our setup), return a typed empty value.
    throw new Error("api client called during SSR — set ssr=false");
  }
  const url = new URL(API_BASE + path, window.location.origin);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
    }
  }
  const headers: Record<string, string> = { Accept: "application/json" };
  const tok = tokenOverride ?? getToken();
  if (tok) headers.Authorization = `Bearer ${tok}`;
  let payload: string | undefined;
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(url.toString(), { method, headers, body: payload });
  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = await res.json();
    } catch {
      detail = await res.text().catch(() => null);
    }
    const msg =
      typeof detail === "object" && detail !== null && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : `${method} ${path} → ${res.status}`;
    throw new ApiError(res.status, detail, msg);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ─── endpoints ──────────────────────────────────────────────────────

export const api = {
  health: () => request<Health>("GET", "/health"),

  // Auth probe — used at app boot to validate a saved token.
  me: (token?: string) => request<User>("GET", "/users/me", undefined, undefined, token),

  // Projects
  listProjects: () => request<Project[]>("GET", "/projects"),
  getProject: (slug: string) => request<Project>("GET", `/projects/${slug}`),
  createProject: (body: { slug: string; name: string; description?: string }) =>
    request<Project>("POST", "/projects", body),

  // Sessions
  createSession: (body: { project: string; title?: string; llm_model?: string }) =>
    request<{ id: string }>("POST", "/sessions", body),

  // Search / facts / decisions
  search: (project: string, q: string, k = 10, includeDecisions = true) =>
    request<SearchOut>("GET", "/search", undefined, {
      project,
      q,
      k,
      include_decisions: includeDecisions,
    }),

  listDecisions: (project: string, limit = 50, since?: string) =>
    request<Decision[]>("GET", "/decisions", undefined, { project, limit, since }),

  logDecision: (body: { project: string; decision: string; rationale: string }) =>
    request<Decision>("POST", "/decisions", body),

  logFact: (body: {
    project: string;
    statement: string;
    entity?: string;
    attribute?: string;
  }) =>
    request<{ id: string; status: string; superseded_id: string | null; refines_id: string | null }>(
      "POST",
      "/facts",
      body,
    ),

  digest: (project: string, depth: "quick" | "standard" | "deep", since?: string, useCache = true) =>
    request<DigestOut>("GET", "/digest", undefined, { project, depth, since, use_cache: useCache }),

  // Users / tokens (admin)
  listUsers: () => request<User[]>("GET", "/users"),
  createUser: (body: { email: string; display_name: string; role: "admin" | "member" }) =>
    request<UserWithToken>("POST", "/users", body),

  listTokens: (userId: string) => request<Token[]>("GET", `/users/${userId}/tokens`),
  issueToken: (userId: string, body: { label?: string; project?: string }) =>
    request<IssuedToken>("POST", `/users/${userId}/tokens`, body),
  revokeToken: (tokenId: string) =>
    request<void>("POST", `/users/tokens/${tokenId}/revoke`),
};
