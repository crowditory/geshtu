// Thin HTTP client that talks to memory-api. The MCP server is a proxy:
// it never holds business logic, only forwards calls.
//
// Uses Node's built-in fetch (Node 20+) instead of axios/got/undici-direct
// to keep the npm install footprint of `@geshtu/mcp` small — every Claude
// Desktop user runs this via `npx -y`, and dependency size matters there.

// Two env names supported. GESHTU_API_URL is the user-facing recommended
// one (matches the GESHTU_TOKEN / GESHTU_USER / GESHTU_PROJECT family).
// API_URL is kept for backward compat with the original 0.1.0 docs and
// the docker-compose wiring where the MCP container talks to api:8000.
const API_URL =
  process.env.GESHTU_API_URL ?? process.env.API_URL ?? "http://api:8000";

export interface ApiOptions {
  token: string;
}

async function request<T>(
  method: string,
  path: string,
  opts: ApiOptions,
  body?: unknown,
  query?: Record<string, string | number | boolean | undefined>,
): Promise<T> {
  const url = new URL(path, API_URL);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
    }
  }
  const headers: Record<string, string> = {
    "Authorization": `Bearer ${opts.token}`,
    "Accept": "application/json",
  };
  let payload: string | undefined;
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(url, { method, headers, body: payload });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`api ${method} ${path} → ${res.status}: ${text.slice(0, 400)}`);
  }
  // Handle 204
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ─── Endpoints ──────────────────────────────────────────────────────

export type Me = {
  id: string;
  email: string;
  display_name: string;
  role: string;
  created_at: string;
  last_seen_at: string;
};

export async function whoami(opts: ApiOptions): Promise<Me> {
  return request("GET", "/users/me", opts);
}

export type SearchedFact = {
  id: string;
  statement: string;
  entity: string | null;
  attribute: string | null;
  score: number;
  valid_from: string;
  confidence: number;
};

export type SearchedDecision = {
  id: string;
  decision: string;
  rationale: string;
  decided_at: string;
  status: string;
  score: number;
};

export async function search(
  opts: ApiOptions,
  args: { project: string; q: string; k?: number; include_decisions?: boolean },
): Promise<{ facts: SearchedFact[]; decisions: SearchedDecision[] }> {
  return request("GET", "/search", opts, undefined, {
    project: args.project,
    q: args.q,
    k: args.k ?? 10,
    include_decisions: args.include_decisions ?? true,
  });
}

export type Decision = {
  id: string;
  project_id: string;
  decision: string;
  rationale: string;
  decided_at: string;
  decided_by: string | null;
  status: string;
};

export async function listDecisions(
  opts: ApiOptions,
  args: { project: string; limit?: number; since?: string },
): Promise<Decision[]> {
  return request("GET", "/decisions", opts, undefined, {
    project: args.project,
    limit: args.limit ?? 10,
    since: args.since,
  });
}

export async function logDecision(
  opts: ApiOptions,
  args: {
    project: string;
    decision: string;
    rationale: string;
    source_session_id?: string;
    source_message_id?: string;
  },
): Promise<Decision> {
  return request("POST", "/decisions", opts, args);
}

export async function logFact(
  opts: ApiOptions,
  args: {
    project: string;
    statement: string;
    entity?: string;
    attribute?: string;
    source_session_id?: string;
    source_message_id?: string;
  },
): Promise<{ id: string; status: string; superseded_id: string | null; refines_id: string | null }> {
  return request("POST", "/facts", opts, args);
}

export async function getDigest(
  opts: ApiOptions,
  args: { project: string; depth?: "quick" | "standard" | "deep"; since?: string },
): Promise<{ id: string; content_md: string; fact_count: number; decision_count: number; cached: boolean }> {
  return request("GET", "/digest", opts, undefined, {
    project: args.project,
    depth: args.depth ?? "standard",
    since: args.since,
  });
}

export async function closeSession(
  opts: ApiOptions,
  args: {
    session_id: string;
    summary_md?: string;
    open_questions?: string[];
    next_actions?: string[];
    auto_summarize?: boolean;
  },
): Promise<{ id: string; summary_id: string; summary_md: string }> {
  const { session_id, ...body } = args;
  return request("POST", `/sessions/${session_id}/close`, opts, body);
}
