#!/usr/bin/env node
// Geshtu MCP server. Speaks MCP over stdio (one server per client process).
//
// This server does NOT verify the token. It just forwards it as a Bearer
// header to memory-api on every call, and the API does the cryptographic
// check (signature + bcrypt + revocation) — that keeps the MCP layer
// dumb and means a leaked JWT_SECRET never ends up shipped to clients.
//
// Required env:
//   GESHTU_TOKEN    — the bearer (starts with `tk_`)
//   GESHTU_API_URL  — base URL of your memory-api (e.g. https://geshtu.playserv.com/api)
// Optional env (recommended):
//   GESHTU_USER     — your email or display name. We call /users/me on
//                     startup and refuse to serve if the token does not
//                     identify this user. Defense in depth + makes config
//                     mistakes loud (you'll see "logged in as alice" if
//                     you copy-pasted alice's token by accident).
//   GESHTU_PROJECT  — project slug to default into tools. With this set,
//                     `geshtu_search` / `_decisions` / `_digest` etc. don't
//                     need a `project` argument every call.

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";

import * as api from "./api.js";

const TOKEN = process.env.GESHTU_TOKEN;
if (!TOKEN || TOKEN.length < 8) {
  console.error("GESHTU_TOKEN env var is required (set in your MCP client config).");
  process.exit(1);
}
const opts: api.ApiOptions = { token: TOKEN };

const EXPECTED_USER = process.env.GESHTU_USER?.trim() || null;
const DEFAULT_PROJECT = process.env.GESHTU_PROJECT?.trim() || null;

// ─── Tool schemas (zod, but rendered to JSON Schema for MCP) ───────────
//
// `project` is OPTIONAL when GESHTU_PROJECT is set in the env. The schema is
// the same either way — at call time we substitute the env default if the
// model didn't pass one. This keeps the tool surface stable across clients
// that do or don't set GESHTU_PROJECT.

const projectField = z
  .string()
  .optional()
  .describe(
    DEFAULT_PROJECT
      ? `Project slug. Optional — defaults to "${DEFAULT_PROJECT}" (configured in this MCP connection).`
      : "Project slug or UUID. Required — no default project is configured.",
  );

const SearchInput = z.object({
  project: projectField,
  query: z.string().min(1).describe("Free-form text to search"),
  k: z.number().int().min(1).max(50).default(10),
});

const DecisionsInput = z.object({
  project: projectField,
  limit: z.number().int().min(1).max(200).default(10),
  since: z.string().optional().describe("ISO date or datetime — only return decisions after this"),
});

const DigestInput = z.object({
  project: projectField,
  since: z.string().optional(),
  depth: z.enum(["quick", "standard", "deep"]).default("standard"),
});

const LogDecisionInput = z.object({
  project: projectField,
  decision: z.string().min(3),
  rationale: z.string().min(3),
  source_session_id: z.string().uuid().optional(),
  source_message_id: z.string().uuid().optional(),
});

const LogFactInput = z.object({
  project: projectField,
  statement: z.string().min(3),
  entity: z.string().optional(),
  attribute: z.string().optional(),
  source_session_id: z.string().uuid().optional(),
  source_message_id: z.string().uuid().optional(),
});

const CloseSessionInput = z.object({
  session_id: z.string().uuid(),
  summary: z.string().optional().describe("Markdown summary; omit to auto-generate"),
  open_questions: z.array(z.string()).default([]),
  next_actions: z.array(z.string()).default([]),
});

// Convert zod → JSON Schema. The SDK accepts plain JSON Schema objects.
// We don't pull in `zod-to-json-schema` because (a) it's a heavy dep for the
// six small shapes we have, and (b) we want the emitted schema to be exactly
// what the model sees — no surprises from the converter's own conventions.
function jsonSchema(s: z.ZodTypeAny): any {
  const def = (s as any)._def;
  if (def.typeName === "ZodObject") {
    const shape = def.shape() as Record<string, z.ZodTypeAny>;
    const properties: Record<string, any> = {};
    const required: string[] = [];
    for (const [k, v] of Object.entries(shape)) {
      properties[k] = jsonSchema(v);
      if (!(v as any).isOptional?.() && !(v as any)._def.defaultValue) {
        required.push(k);
      }
    }
    return { type: "object", properties, required, additionalProperties: false };
  }
  if (def.typeName === "ZodString") return { type: "string", description: def.description };
  if (def.typeName === "ZodNumber") return { type: "integer", description: def.description };
  if (def.typeName === "ZodBoolean") return { type: "boolean" };
  if (def.typeName === "ZodArray") return { type: "array", items: jsonSchema(def.type) };
  if (def.typeName === "ZodEnum") return { type: "string", enum: def.values };
  if (def.typeName === "ZodOptional" || def.typeName === "ZodDefault") {
    return jsonSchema(def.innerType);
  }
  return {};
}

// ─── Server setup ──────────────────────────────────────────────────────

const server = new Server(
  { name: "geshtu", version: "0.2.0" },
  { capabilities: { tools: {} } },
);

const TOOLS = [
  {
    name: "geshtu_search",
    description:
      "Search the team's memory for facts (and active decisions) relevant to a query. " +
      "Use BEFORE answering questions about past work.",
    inputSchema: jsonSchema(SearchInput),
  },
  {
    name: "geshtu_decisions",
    description:
      "List recent decisions for a project, with rationale. Use when the user asks " +
      "what was decided, why, or when.",
    inputSchema: jsonSchema(DecisionsInput),
  },
  {
    name: "geshtu_digest",
    description:
      "Generate an async digest of project activity since a date. depth='quick' " +
      "(~300w), 'standard' (~800w), 'deep' (~2500w). Use for catch-up questions.",
    inputSchema: jsonSchema(DigestInput),
  },
  {
    name: "geshtu_log_decision",
    description:
      "Record an explicit decision (with rationale) made in this conversation. " +
      "Call BEFORE moving on after a 'let's go with X' moment.",
    inputSchema: jsonSchema(LogDecisionInput),
  },
  {
    name: "geshtu_log_fact",
    description:
      "Record an explicit fact (a stable claim about an entity). Call when the user " +
      "says 'remember that...' or 'note that...'.",
    inputSchema: jsonSchema(LogFactInput),
  },
  {
    name: "geshtu_close_session",
    description:
      "Close the current session with a markdown summary, open questions, and " +
      "next actions. Call at session end or every ~20 substantive turns.",
    inputSchema: jsonSchema(CloseSessionInput),
  },
];

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));

function resolveProject(passed: string | undefined): string {
  // Fill in GESHTU_PROJECT if the model didn't pass one. If neither is set,
  // surface a clear actionable error rather than letting the API 422.
  const value = (passed?.trim() || DEFAULT_PROJECT)?.trim();
  if (!value) {
    throw new Error(
      "no project specified and GESHTU_PROJECT env var is not set in this MCP connection",
    );
  }
  return value;
}

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const name = req.params.name;
  const raw = req.params.arguments ?? {};
  try {
    switch (name) {
      case "geshtu_search": {
        const a = SearchInput.parse(raw);
        const out = await api.search(opts, {
          project: resolveProject(a.project),
          q: a.query,
          k: a.k,
        });
        return { content: [{ type: "text", text: JSON.stringify(out, null, 2) }] };
      }
      case "geshtu_decisions": {
        const a = DecisionsInput.parse(raw);
        const out = await api.listDecisions(opts, {
          project: resolveProject(a.project),
          limit: a.limit,
          since: a.since,
        });
        return { content: [{ type: "text", text: JSON.stringify(out, null, 2) }] };
      }
      case "geshtu_digest": {
        const a = DigestInput.parse(raw);
        const out = await api.getDigest(opts, {
          project: resolveProject(a.project),
          since: a.since,
          depth: a.depth,
        });
        return { content: [{ type: "text", text: out.content_md }] };
      }
      case "geshtu_log_decision": {
        const a = LogDecisionInput.parse(raw);
        const out = await api.logDecision(opts, {
          ...a,
          project: resolveProject(a.project),
        });
        return {
          content: [{ type: "text", text: `logged decision ${out.id}` }],
        };
      }
      case "geshtu_log_fact": {
        const a = LogFactInput.parse(raw);
        const out = await api.logFact(opts, {
          ...a,
          project: resolveProject(a.project),
        });
        return {
          content: [
            {
              type: "text",
              text: `${out.status} (id=${out.id}${out.superseded_id ? `, superseded ${out.superseded_id}` : ""}${out.refines_id ? `, refines ${out.refines_id}` : ""})`,
            },
          ],
        };
      }
      case "geshtu_close_session": {
        const a = CloseSessionInput.parse(raw);
        const out = await api.closeSession(opts, {
          session_id: a.session_id,
          summary_md: a.summary,
          open_questions: a.open_questions,
          next_actions: a.next_actions,
          auto_summarize: !a.summary,
        });
        return { content: [{ type: "text", text: out.summary_md }] };
      }
      default:
        throw new Error(`unknown tool: ${name}`);
    }
  } catch (err: any) {
    return {
      isError: true,
      content: [{ type: "text", text: `error: ${err?.message ?? String(err)}` }],
    };
  }
});

// ─── Main ─────────────────────────────────────────────────────────────

async function verifyIdentity(): Promise<void> {
  // Calling /users/me does three useful things at once:
  //   1) confirms the token is valid before MCP starts answering tool calls
  //   2) prints "logged in as X" to stderr so the operator sees who the
  //      client is connected as (helps catch wrong-token-in-config mistakes)
  //   3) if GESHTU_USER is configured, hard-fails when the token doesn't
  //      identify that user — the user-id-as-second-factor check.
  let me;
  try {
    me = await api.whoami(opts);
  } catch (err: any) {
    console.error(`Geshtu auth failed: ${err?.message ?? err}`);
    process.exit(2);
  }
  console.error(
    `Geshtu MCP: connected as ${me.display_name} <${me.email}> (${me.role})` +
      (DEFAULT_PROJECT ? ` · project=${DEFAULT_PROJECT}` : "") +
      ` · api=${process.env.API_URL ?? process.env.GESHTU_API_URL ?? "default"}`,
  );
  if (EXPECTED_USER) {
    const expected = EXPECTED_USER.toLowerCase();
    if (
      me.email.toLowerCase() !== expected &&
      me.display_name.toLowerCase() !== expected &&
      me.id !== EXPECTED_USER
    ) {
      console.error(
        `Geshtu MCP: GESHTU_USER=${EXPECTED_USER} but the token identifies ${me.email}. Refusing to start.`,
      );
      process.exit(3);
    }
  }
}

async function main(): Promise<void> {
  await verifyIdentity();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // The SDK keeps the process alive while the transport is connected.
}

main().catch((err) => {
  console.error("MCP server fatal:", err);
  process.exit(1);
});
