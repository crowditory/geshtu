<script lang="ts">
  import { Search } from "lucide-svelte";
  import { ApiError, api } from "$lib/api/client";
  import { activeProjectSlug } from "$lib/stores/project";
  import { toastError } from "$lib/stores/toast";
  import Card from "$lib/components/ui/Card.svelte";
  import Input from "$lib/components/ui/Input.svelte";
  import Skeleton from "$lib/components/ui/Skeleton.svelte";
  import Badge from "$lib/components/ui/Badge.svelte";
  import { fmtDate } from "$lib/utils";
  import type { SearchOut } from "$lib/api/types";

  let q = $state("");
  let result = $state<SearchOut | null>(null);
  let loading = $state(false);
  let timer: ReturnType<typeof setTimeout> | undefined;

  function debounce() {
    clearTimeout(timer);
    timer = setTimeout(run, 250);
  }

  async function run() {
    if (!$activeProjectSlug || !q.trim()) {
      result = null;
      return;
    }
    loading = true;
    try {
      result = await api.search($activeProjectSlug, q.trim(), 20);
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Search failed");
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head><title>Facts — Geshtu</title></svelte:head>

<header class="mb-6">
  <h1 class="text-3xl font-semibold tracking-tight">Facts</h1>
  <p class="mt-1 text-sm text-muted-foreground">
    Hybrid search: vector similarity + keyword, fused via Reciprocal Rank Fusion.
  </p>
</header>

{#if !$activeProjectSlug}
  <Card class="p-6 text-center text-sm text-muted-foreground">
    Pick a project from the sidebar.
  </Card>
{:else}
  <div class="relative mb-6">
    <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
    <Input
      placeholder="Search facts and decisions in {$activeProjectSlug}…"
      class="pl-9"
      bind:value={q}
      oninput={debounce}
      autofocus
    />
  </div>

  {#if loading}
    <div class="space-y-3">
      <Skeleton class="h-16 w-full" />
      <Skeleton class="h-16 w-full" />
      <Skeleton class="h-16 w-full" />
    </div>
  {:else if !q.trim()}
    <Card class="p-6 text-center text-sm text-muted-foreground">
      Type a query above to search.
    </Card>
  {:else if result}
    <div class="mb-3 flex items-center gap-3 text-xs text-muted-foreground">
      <Badge variant="outline">{result.facts.length} facts</Badge>
      <Badge variant="outline">{result.decisions.length} decisions</Badge>
    </div>

    {#if result.facts.length}
      <h2 class="mb-2 text-sm font-medium text-muted-foreground">Facts</h2>
      <div class="mb-6 space-y-2">
        {#each result.facts as f}
          <Card class="p-4">
            <div class="font-medium">{f.statement}</div>
            <div class="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
              {#if f.entity}<Badge variant="secondary">{f.entity}</Badge>{/if}
              {#if f.attribute}<Badge variant="secondary">{f.attribute}</Badge>{/if}
              <span>· score {f.score.toFixed(3)}</span>
              <span>· valid from {fmtDate(f.valid_from)}</span>
            </div>
          </Card>
        {/each}
      </div>
    {/if}

    {#if result.decisions.length}
      <h2 class="mb-2 text-sm font-medium text-muted-foreground">Related decisions</h2>
      <div class="space-y-2">
        {#each result.decisions as d}
          <Card class="p-4">
            <div class="font-medium">{d.decision}</div>
            <p class="mt-1 text-sm text-muted-foreground">{d.rationale}</p>
            <div class="mt-2 text-xs text-muted-foreground">{fmtDate(d.decided_at)} · score {d.score.toFixed(3)}</div>
          </Card>
        {/each}
      </div>
    {/if}

    {#if result.facts.length === 0 && result.decisions.length === 0}
      <Card class="p-6 text-center text-sm text-muted-foreground">
        No matches.
      </Card>
    {/if}
  {/if}
{/if}
