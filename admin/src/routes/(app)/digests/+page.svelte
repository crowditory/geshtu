<script lang="ts">
  import { Sparkles } from "lucide-svelte";
  import { ApiError, api } from "$lib/api/client";
  import { activeProjectSlug } from "$lib/stores/project";
  import { toastError } from "$lib/stores/toast";
  import Card from "$lib/components/ui/Card.svelte";
  import Button from "$lib/components/ui/Button.svelte";
  import Badge from "$lib/components/ui/Badge.svelte";
  import { cn } from "$lib/utils";
  import type { DigestOut } from "$lib/api/types";

  type Depth = "quick" | "standard" | "deep";
  let depth = $state<Depth>("standard");
  let since = $state("");
  let useCache = $state(true);
  let result = $state<DigestOut | null>(null);
  let loading = $state(false);

  async function generate() {
    if (!$activeProjectSlug) return;
    loading = true; result = null;
    try {
      result = await api.digest($activeProjectSlug, depth, since.trim() || undefined, useCache);
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Digest failed");
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head><title>Digests — Geshtu</title></svelte:head>

<header class="mb-6">
  <h1 class="text-3xl font-semibold tracking-tight">Digests</h1>
  <p class="mt-1 text-sm text-muted-foreground">
    Markdown summary of project activity, three depths.
    Quick (~300 words), Standard (~800), Deep (~2,500).
  </p>
</header>

{#if !$activeProjectSlug}
  <Card class="p-6 text-center text-sm text-muted-foreground">Pick a project from the sidebar.</Card>
{:else}
  <Card class="p-5">
    <div class="grid grid-cols-1 gap-4 md:grid-cols-[auto_1fr_auto_auto]">
      <div class="inline-flex rounded-lg border bg-secondary/30 p-1 text-sm">
        {#each ["quick", "standard", "deep"] as d}
          <button
            type="button"
            onclick={() => (depth = d as Depth)}
            class={cn(
              "rounded-md px-3 py-1 capitalize transition-colors",
              depth === d ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {d}
          </button>
        {/each}
      </div>
      <input
        type="date"
        bind:value={since}
        placeholder="Since"
        class="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
      />
      <label class="inline-flex items-center gap-2 text-sm text-muted-foreground">
        <input type="checkbox" bind:checked={useCache} class="h-4 w-4 rounded" />
        Use 1h cache
      </label>
      <Button onclick={generate} loading={loading}>
        <Sparkles class="h-4 w-4" />
        Generate
      </Button>
    </div>
  </Card>

  {#if result}
    <div class="mt-6">
      <div class="mb-3 flex items-center gap-2 text-xs text-muted-foreground">
        <Badge variant={result.cached ? "secondary" : "default"}>
          {result.cached ? "cached" : "fresh"}
        </Badge>
        <span>{result.fact_count} facts · {result.decision_count} decisions</span>
      </div>
      <Card class="p-6">
        <pre class="whitespace-pre-wrap font-sans text-sm leading-relaxed">{result.content_md}</pre>
      </Card>
    </div>
  {/if}
{/if}
