<script lang="ts">
  import { Plus } from "lucide-svelte";
  import { ApiError, api } from "$lib/api/client";
  import { user } from "$lib/stores/auth";
  import { projects, activeProjectSlug } from "$lib/stores/project";
  import { toastError, toastSuccess } from "$lib/stores/toast";
  import Card from "$lib/components/ui/Card.svelte";
  import Button from "$lib/components/ui/Button.svelte";
  import Input from "$lib/components/ui/Input.svelte";
  import Label from "$lib/components/ui/Label.svelte";
  import Sheet from "$lib/components/ui/Sheet.svelte";
  import { fmtDate } from "$lib/utils";

  let openCreate = $state(false);
  let slug = $state("");
  let name = $state("");
  let description = $state("");
  let saving = $state(false);

  async function create(e: SubmitEvent) {
    e.preventDefault();
    if (!slug.trim() || !name.trim()) return;
    saving = true;
    try {
      const p = await api.createProject({
        slug: slug.trim(),
        name: name.trim(),
        description: description.trim() || undefined,
      });
      projects.update((arr) => [p, ...arr]);
      activeProjectSlug.set(p.slug);
      toastSuccess(`Created ${p.slug}`);
      openCreate = false;
      slug = ""; name = ""; description = "";
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Failed to create project");
    } finally {
      saving = false;
    }
  }
</script>

<svelte:head><title>Projects — Geshtu</title></svelte:head>

<header class="mb-8 flex items-center justify-between">
  <div>
    <h1 class="text-3xl font-semibold tracking-tight">Projects</h1>
    <p class="mt-1 text-sm text-muted-foreground">
      Memory is scoped per-project. Add one for each product/team you work on.
    </p>
  </div>
  {#if $user?.role === "admin"}
    <Button onclick={() => (openCreate = true)}>
      <Plus class="h-4 w-4" />
      New project
    </Button>
  {/if}
</header>

{#if $projects.length === 0}
  <Card class="p-12 text-center">
    <p class="text-sm text-muted-foreground">
      No projects yet. {$user?.role === "admin" ? "Create one above." : "Ask an admin to create one."}
    </p>
  </Card>
{:else}
  <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
    {#each $projects as p}
      <Card class="p-4">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <div class="font-semibold">{p.name}</div>
            <div class="text-xs text-muted-foreground">{p.slug}</div>
            {#if p.description}<p class="mt-2 text-sm">{p.description}</p>{/if}
          </div>
          <button
            type="button"
            onclick={() => activeProjectSlug.set(p.slug)}
            class="rounded-md border px-2 py-1 text-xs font-medium transition-colors hover:bg-accent"
            class:bg-primary={p.slug === $activeProjectSlug}
            class:text-primary-foreground={p.slug === $activeProjectSlug}
            class:border-primary={p.slug === $activeProjectSlug}
          >
            {p.slug === $activeProjectSlug ? "Active" : "Activate"}
          </button>
        </div>
        <div class="mt-3 text-xs text-muted-foreground">
          Created {fmtDate(p.created_at)}
        </div>
      </Card>
    {/each}
  </div>
{/if}

<Sheet bind:open={openCreate} title="New project" description="Slug must be lowercase, dashes only.">
  <form class="space-y-4" onsubmit={create}>
    <div class="space-y-1.5">
      <Label for="p-slug">Slug</Label>
      <Input id="p-slug" placeholder="playserv-billing" required bind:value={slug} />
    </div>
    <div class="space-y-1.5">
      <Label for="p-name">Name</Label>
      <Input id="p-name" placeholder="PlayServ Billing" required bind:value={name} />
    </div>
    <div class="space-y-1.5">
      <Label for="p-desc">Description (optional)</Label>
      <Input id="p-desc" placeholder="…" bind:value={description} />
    </div>
    <div class="flex justify-end gap-2 pt-2">
      <Button variant="ghost" onclick={() => (openCreate = false)}>Cancel</Button>
      <Button type="submit" loading={saving}>Create</Button>
    </div>
  </form>
</Sheet>
