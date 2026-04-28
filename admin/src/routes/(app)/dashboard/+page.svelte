<script lang="ts">
  import { onMount } from "svelte";
  import { Activity, FolderKanban, Users, Database, Plug, ArrowRight } from "lucide-svelte";
  import Card from "$lib/components/ui/Card.svelte";
  import Skeleton from "$lib/components/ui/Skeleton.svelte";
  import Badge from "$lib/components/ui/Badge.svelte";
  import Button from "$lib/components/ui/Button.svelte";
  import { api } from "$lib/api/client";
  import { user } from "$lib/stores/auth";
  import { projects, activeProjectSlug } from "$lib/stores/project";
  import { fmtDate } from "$lib/utils";
  import type { Decision, Health, User } from "$lib/api/types";

  let health = $state<Health | null>(null);
  let users = $state<User[]>([]);
  let recentDecisions = $state<Decision[]>([]);
  let loading = $state(true);

  $effect(() => {
    const slug = $activeProjectSlug;
    if (!slug) { recentDecisions = []; return; }
    loading = true;
    (async () => {
      try {
        recentDecisions = await api.listDecisions(slug, 5);
      } catch { recentDecisions = []; }
      finally { loading = false; }
    })();
  });

  onMount(async () => {
    try { health = await api.health(); } catch { /* skip */ }
    if ($user?.role === "admin") {
      try { users = await api.listUsers(); } catch { /* skip */ }
    }
  });
</script>

<svelte:head><title>Dashboard — Geshtu</title></svelte:head>

<header class="mb-8">
  <h1 class="text-3xl font-semibold tracking-tight">Dashboard</h1>
  <p class="mt-1 text-sm text-muted-foreground">
    {#if $user}Welcome, {$user.display_name}.{/if}
  </p>
</header>

{#if $projects.length === 0}
  <!-- First-run state. Replaces all the metrics/decisions noise with a clear
       two-step path: create a project, then go to Connect. -->
  <section class="grid grid-cols-1 gap-4 md:grid-cols-2">
    <Card class="p-8">
      <div class="flex items-start gap-4">
        <span class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
          <FolderKanban class="h-5 w-5" />
        </span>
        <div class="flex-1">
          <h2 class="text-lg font-semibold">Create your first project</h2>
          <p class="mt-1 text-sm text-muted-foreground">
            Memory is scoped per-project. Make one for the codebase / product
            you want the team's LLMs to share context about.
          </p>
          {#if $user?.role === "admin"}
            <div class="mt-4">
              <Button href="/projects">
                Add a project
                <ArrowRight class="h-4 w-4" />
              </Button>
            </div>
          {:else}
            <p class="mt-4 text-sm text-muted-foreground">
              Ask your admin to create one — only admins can.
            </p>
          {/if}
        </div>
      </div>
    </Card>
    <Card class="p-8">
      <div class="flex items-start gap-4">
        <span class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Plug class="h-5 w-5" />
        </span>
        <div class="flex-1">
          <h2 class="text-lg font-semibold">Then connect your AI client</h2>
          <p class="mt-1 text-sm text-muted-foreground">
            Generate a token, copy a JSON config snippet for Claude Desktop / Cursor / Windsurf,
            paste the team protocol. Three steps, one page.
          </p>
          <div class="mt-4">
            <Button href="/connect" variant="outline">
              Open Connect
              <ArrowRight class="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </Card>
  </section>
{:else}

<section class="grid grid-cols-2 gap-4 md:grid-cols-4">
  <Card class="p-4">
    <div class="flex items-center gap-2 text-xs text-muted-foreground">
      <FolderKanban class="h-3.5 w-3.5" /> Projects
    </div>
    <div class="mt-2 text-2xl font-semibold">{$projects.length}</div>
  </Card>
  <Card class="p-4">
    <div class="flex items-center gap-2 text-xs text-muted-foreground">
      <Users class="h-3.5 w-3.5" /> Users
    </div>
    <div class="mt-2 text-2xl font-semibold">{users.length || "—"}</div>
  </Card>
  <Card class="p-4">
    <div class="flex items-center gap-2 text-xs text-muted-foreground">
      <Activity class="h-3.5 w-3.5" /> API
    </div>
    <div class="mt-2">
      {#if health}
        <Badge variant={health.status === "ok" ? "success" : "destructive"}>{health.status}</Badge>
      {:else}
        <Skeleton class="h-5 w-12" />
      {/if}
    </div>
  </Card>
  <Card class="p-4">
    <div class="flex items-center gap-2 text-xs text-muted-foreground">
      <Database class="h-3.5 w-3.5" /> Active project
    </div>
    <div class="mt-2 truncate text-2xl font-semibold">{$activeProjectSlug ?? "—"}</div>
  </Card>
</section>

<section class="mt-10">
  <div class="mb-3 flex items-baseline justify-between">
    <h2 class="text-lg font-semibold">Recent decisions</h2>
    <a href="/decisions" class="text-xs text-muted-foreground hover:text-foreground">View all →</a>
  </div>

  {#if !$activeProjectSlug}
    <Card class="p-6 text-center text-sm text-muted-foreground">
      Pick a project from the sidebar to see decisions.
    </Card>
  {:else if loading}
    <div class="space-y-3">
      <Skeleton class="h-20 w-full" />
      <Skeleton class="h-20 w-full" />
    </div>
  {:else if recentDecisions.length === 0}
    <Card class="p-6 text-center text-sm text-muted-foreground">
      No decisions yet. They appear when extraction picks them up from
      messages, or when you call <code>geshtu_log_decision</code>.
    </Card>
  {:else}
    <div class="space-y-3">
      {#each recentDecisions as d}
        <Card class="p-4">
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1">
              <div class="font-medium">{d.decision}</div>
              <p class="mt-1 text-sm text-muted-foreground">{d.rationale}</p>
            </div>
            <Badge variant={d.status === "active" ? "success" : "outline"}>{d.status}</Badge>
          </div>
          <div class="mt-3 text-xs text-muted-foreground">{fmtDate(d.decided_at)}</div>
        </Card>
      {/each}
    </div>
  {/if}
</section>
{/if}
