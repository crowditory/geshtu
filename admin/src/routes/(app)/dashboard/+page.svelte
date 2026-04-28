<script lang="ts">
  import { onMount } from "svelte";
  import { Activity, FolderKanban, Users, Database } from "lucide-svelte";
  import Card from "$lib/components/ui/Card.svelte";
  import Skeleton from "$lib/components/ui/Skeleton.svelte";
  import Badge from "$lib/components/ui/Badge.svelte";
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
