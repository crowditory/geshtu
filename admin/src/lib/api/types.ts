// Mirrors the FastAPI Pydantic shapes from api/geshtu/routes/*.

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: "admin" | "member";
  created_at: string;
  last_seen_at: string;
}

export interface Project {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface Decision {
  id: string;
  project_id: string;
  decision: string;
  rationale: string;
  decided_at: string;
  decided_by: string | null;
  status: "active" | "reversed" | "superseded";
}

export interface SearchedFact {
  id: string;
  statement: string;
  entity: string | null;
  attribute: string | null;
  score: number;
  valid_from: string;
  confidence: number;
}

export interface SearchedDecision {
  id: string;
  decision: string;
  rationale: string;
  decided_at: string;
  status: string;
  score: number;
}

export interface SearchOut {
  facts: SearchedFact[];
  decisions: SearchedDecision[];
}

export interface DigestOut {
  id: string;
  content_md: string;
  fact_count: number;
  decision_count: number;
  cached: boolean;
}

export interface Token {
  id: string;
  label: string | null;
  project_id: string | null;
  project_slug: string | null;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface IssuedToken {
  id: string;
  token: string;
  label: string | null;
  project_id: string | null;
  project_slug: string | null;
}

export interface UserWithToken extends User {
  token: string;
}

export interface Health {
  status: "ok" | "degraded";
  version: string;
  db: boolean;
}
