<script lang="ts">
  import { Plus } from "lucide-svelte";
  import { ApiError, api } from "$lib/api/client";
  import { activeProjectSlug } from "$lib/stores/project";
  import { toastError, toastSuccess } from "$lib/stores/toast";
  import Card from "$lib/components/ui/Card.svelte";
  import Button from "$lib/components/ui/Button.svelte";
  import Badge from "$lib/components/ui/Badge.svelte";
  import Skeleton from "$lib/components/ui/Skeleton.svelte";
  import Sheet from "$lib/components/ui/Sheet.svelte";
  import Input from "$lib/components/ui/Input.svelte";
  import Label from "$lib/components/ui/Label.svelte";
  import { fmtDate } from "$lib/utils";
  import type { Decision } from "$lib/api/types";

  let rows = $state<Decision[]>([]);
  let loading = $state(true);
  let openLog = $state(false);
  let dec = $state("");
  let rat = $state("");
  let saving = $state(false);

  $effect(() => {
    const slug = $activeProjectSlug;
    if (!slug) { rows = []; loading = false; return; }
    loading = true;
    (async () => {
      try { rows = await api.listDecisions(slug, 100); }
      catch { rows = []; }
      finally { loading = false; }
    })();
  });

  async function save(e: SubmitEvent) {
    e.preventDefault();
    if (!$activeProjectSlug || dec.trim().length < 3 || rat.trim().length < 3) return;
    saving = true;
    try {
      const d = await api.logDecision({
        project: $activeProjectSlug,
        decision: dec.trim(),
        rationale: rat.trim(),
      });
      rows = [d, ...rows];
      toastSuccess("Decision logged");
      openLog = false;
      dec = ""; rat = "";
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Failed to log decision");
    } finally {
      saving = false;
    }
  }
</script>

<svelte:head><title>Decisions — Geshtu</title></svelte:head>

<header class="mb-6 flex items-start justify-between">
  <div>
    <h1 class="text-3xl font-semibold tracking-tight">Decisions</h1>
    <p class="mt-1 text-sm text-muted-foreground">
      Choices the team has made, with rationale. Required field — not optional.
    </p>
  </div>
  {#if $activeProjectSlug}
    <Button onclick={() => (openLog = true)}>
      <Plus class="h-4 w-4" /> Log decision
    </Button>
  {/if}
</header>

{#if !$activeProjectSlug}
  <Card class="p-6 text-center text-sm text-muted-foreground">Pick a project from the sidebar.</Card>
{:else if loading}
  <div class="space-y-3">
    <Skeleton class="h-24 w-full" />
    <Skeleton class="h-24 w-full" />
  </div>
{:else if rows.length === 0}
  <Card class="p-12 text-center text-sm text-muted-foreground">
    No decisions yet. Log one above, or have your AI call <code>geshtu_log_decision</code>.
  </Card>
{:else}
  <div class="space-y-3">
    {#each rows as d}
      <Card class="p-4">
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1">
            <div class="font-medium">{d.decision}</div>
            <p class="mt-1.5 text-sm text-muted-foreground">{d.rationale}</p>
          </div>
          <Badge variant={d.status === "active" ? "success" : "outline"}>{d.status}</Badge>
        </div>
        <div class="mt-3 text-xs text-muted-foreground">{fmtDate(d.decided_at)}</div>
      </Card>
    {/each}
  </div>
{/if}

<Sheet bind:open={openLog} title="Log decision">
  <form class="space-y-4" onsubmit={save}>
    <div class="space-y-1.5">
      <Label for="dec">Decision</Label>
      <Input id="dec" placeholder="Use Postgres for the new service" required bind:value={dec} />
    </div>
    <div class="space-y-1.5">
      <Label for="rat">Rationale</Label>
      <textarea
        id="rat"
        rows="4"
        required
        bind:value={rat}
        placeholder="Why this choice over the alternatives?"
        class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      ></textarea>
    </div>
    <div class="flex justify-end gap-2 pt-2">
      <Button variant="ghost" onclick={() => (openLog = false)}>Cancel</Button>
      <Button type="submit" loading={saving}>Log</Button>
    </div>
  </form>
</Sheet>
