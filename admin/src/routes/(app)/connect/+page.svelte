<script lang="ts">
  import { Copy, Check, KeyRound, RotateCw, ChevronDown } from "lucide-svelte";
  import { ApiError, api } from "$lib/api/client";
  import { user } from "$lib/stores/auth";
  import { activeProjectSlug, projects } from "$lib/stores/project";
  import { toastError, toastSuccess } from "$lib/stores/toast";
  import Card from "$lib/components/ui/Card.svelte";
  import Button from "$lib/components/ui/Button.svelte";
  import Input from "$lib/components/ui/Input.svelte";
  import Label from "$lib/components/ui/Label.svelte";
  import Badge from "$lib/components/ui/Badge.svelte";
  import { cn } from "$lib/utils";

  // ─── State ───────────────────────────────────────────────────────

  // The token we ISSUE on this page. `null` until the user clicks "Generate
  // a fresh token" — we never auto-mint one to avoid creating clutter just
  // because someone opened the page.
  let issuedToken = $state<string | null>(null);
  let issuing = $state(false);
  let scopeProject = $state<string>("");          // "" = all projects
  let labelInput = $state("");
  let copiedKey = $state<string | null>(null);   // which copy button was last clicked

  // The base URL the MCP client should hit. Same origin as the admin SPA
  // — Caddy routes /api/* to memory-api. If the admin is opened on
  // localhost (dev) we still want to suggest a sensible production URL,
  // so we expose it but make it editable.
  let apiUrl = $state(
    typeof window !== "undefined"
      ? `${window.location.origin}/api`
      : "https://geshtu.example.com/api",
  );

  let client = $state<"claude-desktop" | "cursor" | "windsurf" | "json">(
    "claude-desktop",
  );

  // ─── Derived values ──────────────────────────────────────────────

  const tokenForSnippet = $derived(issuedToken ?? "tk_<paste-your-token>");
  const projectForSnippet = $derived(scopeProject || $activeProjectSlug || "<your-project-slug>");
  const emailForSnippet = $derived($user?.email ?? "<your-email>");

  const claudeDesktopJSON = $derived(
    JSON.stringify(
      {
        mcpServers: {
          [`geshtu-${projectForSnippet}`]: {
            command: "npx",
            args: ["-y", "@geshtu/mcp"],
            env: {
              GESHTU_TOKEN: tokenForSnippet,
              GESHTU_API_URL: apiUrl,
              GESHTU_EMAIL: emailForSnippet,
              GESHTU_PROJECT: projectForSnippet,
            },
          },
        },
      },
      null,
      2,
    ),
  );

  // The team protocol is the same string as docs/team-protocol.md, with
  // {{PROJECT_SLUG}} substituted. Kept inline so the SPA needs no extra
  // round-trip to render it.
  const teamProtocol = $derived(`# Team Memory Protocol — Geshtu
You have access to the team's shared memory via \`geshtu_*\` tools.
Project slug: ${projectForSnippet}.

## Before answering substantive questions
1. If the user references past work ("our plan", "we decided",
   "the architecture"), call \`geshtu_search\` with key terms.
2. If the user starts with a catch-up question ("what's new",
   "where are we"), call \`geshtu_digest\` with depth='quick' first.
3. Treat retrieved facts as ground truth. If the user contradicts
   them, ASK whether to update — don't silently overwrite.

## During the conversation
- When the user makes an explicit decision ("let's go with X"),
  call \`geshtu_log_decision\` BEFORE moving on, capturing
  both the decision and the rationale.
- When the user says "remember that..." or "note that...",
  call \`geshtu_log_fact\`.

## At session end (or every 20 substantive turns)
- Call \`geshtu_close_session\` with a brief markdown summary,
  open questions, and next actions.

## Citation rules
- When using a retrieved fact, cite briefly: "(per memory, Apr 12)".
- When facts and the current message conflict, surface the conflict.
- Never invent a fact or rationale not in memory or this conversation.`);

  // ─── Per-client setup metadata ───────────────────────────────────

  const clients = [
    {
      key: "claude-desktop",
      label: "Claude Desktop",
      configPath: {
        macOS: "~/Library/Application Support/Claude/claude_desktop_config.json",
        Windows: "%APPDATA%\\Claude\\claude_desktop_config.json",
        Linux: "~/.config/Claude/claude_desktop_config.json",
      },
      restart: "Fully quit Claude (not just close the window) and reopen.",
    },
    {
      key: "cursor",
      label: "Cursor",
      configPath: {
        "Project-level": ".cursor/mcp.json",
        Global: "~/.cursor/mcp.json",
      },
      restart: "Cursor → Settings → MCP → reload.",
    },
    {
      key: "windsurf",
      label: "Windsurf",
      configPath: {
        Default: "~/.codeium/windsurf/mcp_config.json",
      },
      restart: "Windsurf → Settings → MCP servers → refresh.",
    },
    {
      key: "json",
      label: "Generic JSON",
      configPath: { "Wherever your client expects MCP servers": "" },
      restart: "Reload your MCP client per its own instructions.",
    },
  ] as const;

  const currentClient = $derived(clients.find((c) => c.key === client) ?? clients[0]);

  // ─── Actions ─────────────────────────────────────────────────────

  async function issue() {
    issuing = true;
    try {
      const r = await api.issueMyToken({
        label: labelInput.trim() || `connect-${new Date().toISOString().slice(0, 10)}`,
        project: scopeProject || undefined,
      });
      issuedToken = r.token;
      toastSuccess("Token issued. Copy it now — it won't be shown again.");
      labelInput = "";
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Failed to issue token");
    } finally {
      issuing = false;
    }
  }

  async function copy(text: string, key: string) {
    try {
      await navigator.clipboard.writeText(text);
      copiedKey = key;
      setTimeout(() => (copiedKey = null), 1500);
    } catch {
      toastError("Clipboard blocked — copy manually.");
    }
  }
</script>

<svelte:head><title>Connect — Geshtu</title></svelte:head>

<header class="mb-8">
  <h1 class="text-3xl font-semibold tracking-tight">Connect</h1>
  <p class="mt-1 text-sm text-muted-foreground">
    Wire your AI client to this Geshtu instance in three steps: issue a token,
    paste the config, drop in the team protocol.
  </p>
</header>

<!-- Step 1: token -->
<section class="mb-8">
  <div class="mb-3 flex items-baseline gap-3">
    <span class="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">1</span>
    <h2 class="text-lg font-semibold">Get a token</h2>
  </div>
  <Card class="p-5">
    {#if issuedToken}
      <div class="space-y-3">
        <div class="rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-sm">
          <strong>Copy this token now.</strong> It is not stored in cleartext on
          the server, so we cannot show it to you again.
        </div>
        <div class="flex gap-2">
          <Input value={issuedToken} class="font-mono" />
          <Button variant="outline" size="icon" onclick={() => copy(issuedToken!, "token")}>
            {#if copiedKey === "token"}<Check class="h-4 w-4" />{:else}<Copy class="h-4 w-4" />{/if}
          </Button>
        </div>
        <div class="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          {#if scopeProject}
            <Badge variant="default">project: {scopeProject}</Badge>
          {:else}
            <Badge variant="outline">all projects</Badge>
          {/if}
          <span>· Issued {new Date().toISOString().slice(0, 16).replace("T", " ")}</span>
          <button
            type="button"
            onclick={() => { issuedToken = null; }}
            class="ml-auto inline-flex items-center gap-1 rounded-md px-2 py-1 hover:bg-accent hover:text-foreground"
          >
            <RotateCw class="h-3.5 w-3.5" /> Issue another
          </button>
        </div>
      </div>
    {:else}
      <div class="grid grid-cols-1 gap-3 md:grid-cols-[1fr_1fr_auto]">
        <div class="space-y-1.5">
          <Label for="t-label">Label</Label>
          <Input id="t-label" placeholder="alice's laptop" bind:value={labelInput} />
        </div>
        <div class="space-y-1.5">
          <Label for="t-scope">Scope</Label>
          <select
            id="t-scope"
            bind:value={scopeProject}
            class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="">All projects</option>
            {#each $projects as p}
              <option value={p.slug}>{p.name} ({p.slug})</option>
            {/each}
          </select>
        </div>
        <div class="self-end">
          <Button onclick={issue} loading={issuing} class="w-full md:w-auto">
            <KeyRound class="h-4 w-4" />
            Generate
          </Button>
        </div>
      </div>
      <p class="mt-3 text-xs text-muted-foreground">
        Tip: scope to one project so a leaked token can't reach others.
      </p>
    {/if}
  </Card>
</section>

<!-- Step 2: client config -->
<section class="mb-8">
  <div class="mb-3 flex items-baseline gap-3">
    <span class="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">2</span>
    <h2 class="text-lg font-semibold">Configure your AI client</h2>
  </div>

  <!-- client picker tabs -->
  <div class="mb-3 inline-flex rounded-lg border bg-secondary/30 p-1 text-sm">
    {#each clients as c}
      <button
        type="button"
        onclick={() => (client = c.key)}
        class={cn(
          "rounded-md px-3 py-1 transition-colors",
          client === c.key ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground",
        )}
      >
        {c.label}
      </button>
    {/each}
  </div>

  <Card class="p-5">
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      <div>
        <div class="text-xs uppercase tracking-wider text-muted-foreground">Config file location</div>
        <dl class="mt-2 space-y-1 text-sm">
          {#each Object.entries(currentClient.configPath) as [os, path]}
            <div class="flex items-baseline gap-2">
              <dt class="w-32 flex-shrink-0 text-muted-foreground">{os}</dt>
              <dd class="font-mono text-xs">{path || "—"}</dd>
            </div>
          {/each}
        </dl>
      </div>
      <div>
        <div class="text-xs uppercase tracking-wider text-muted-foreground">After saving</div>
        <p class="mt-2 text-sm">{currentClient.restart}</p>
      </div>
    </div>

    <div class="mt-4">
      <div class="mb-2 flex items-baseline justify-between">
        <Label>Paste this JSON</Label>
        <button
          type="button"
          onclick={() => copy(claudeDesktopJSON, "config")}
          class="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
        >
          {#if copiedKey === "config"}
            <Check class="h-3.5 w-3.5" /> Copied
          {:else}
            <Copy class="h-3.5 w-3.5" /> Copy
          {/if}
        </button>
      </div>
      <pre class="overflow-x-auto rounded-md border bg-secondary/30 p-4 text-xs leading-relaxed">{claudeDesktopJSON}</pre>
    </div>

    <div class="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
      <div class="space-y-1.5">
        <Label for="api-url">API URL</Label>
        <Input id="api-url" bind:value={apiUrl} class="font-mono text-xs" />
        <p class="text-xs text-muted-foreground">
          Defaults to this admin's origin + <code>/api</code>. Override if your
          MCP client is on a different host.
        </p>
      </div>
      <div class="space-y-1.5">
        <Label>What you'll see on first launch</Label>
        <Card class="bg-secondary/30 p-3 font-mono text-xs">
          Geshtu MCP: connected as {$user?.display_name ?? "?"} &lt;{emailForSnippet}&gt; · project={projectForSnippet}
        </Card>
        <p class="text-xs text-muted-foreground">
          If the line says someone unexpected, fix the token before the AI starts using it.
        </p>
      </div>
    </div>
  </Card>
</section>

<!-- Step 3: team protocol -->
<section class="mb-8">
  <div class="mb-3 flex items-baseline gap-3">
    <span class="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">3</span>
    <h2 class="text-lg font-semibold">Tell the AI when to use the tools</h2>
  </div>
  <Card class="p-5">
    <p class="mb-3 text-sm text-muted-foreground">
      Drop this block into your AI's system prompt or rules file
      (Project Instructions in Claude Desktop, <code>.cursor/rules</code> in Cursor,
      <code>.windsurfrules</code> in Windsurf). Without it, the model often
      forgets the tools exist.
    </p>
    <div class="mb-2 flex items-baseline justify-between">
      <Label>Team protocol</Label>
      <button
        type="button"
        onclick={() => copy(teamProtocol, "protocol")}
        class="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
      >
        {#if copiedKey === "protocol"}
          <Check class="h-3.5 w-3.5" /> Copied
        {:else}
          <Copy class="h-3.5 w-3.5" /> Copy
        {/if}
      </button>
    </div>
    <pre class="max-h-96 overflow-y-auto rounded-md border bg-secondary/30 p-4 text-xs leading-relaxed">{teamProtocol}</pre>
  </Card>
</section>

<!-- Sharing teammates -->
{#if $user?.role === "admin"}
  <section>
    <div class="mb-3 flex items-baseline gap-3">
      <span class="flex h-7 w-7 items-center justify-center rounded-full bg-secondary text-sm font-semibold">+</span>
      <h2 class="text-lg font-semibold">Onboarding teammates</h2>
    </div>
    <Card class="p-5 text-sm">
      <ol class="ml-5 list-decimal space-y-1 text-muted-foreground">
        <li>Add the teammate on the <a href="/users" class="text-primary hover:underline">Users page</a>.</li>
        <li>Issue them a project-scoped token on the <a href="/tokens" class="text-primary hover:underline">Tokens page</a>.</li>
        <li>Send them the token plus this Connect page link — they paste their token into the field above and copy the same JSON / protocol blocks.</li>
      </ol>
    </Card>
  </section>
{/if}
