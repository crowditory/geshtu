<script lang="ts">
  import { ChevronsUpDown, Check, FolderPlus } from "lucide-svelte";
  import { goto } from "$app/navigation";
  import { activeProjectSlug, projects } from "$lib/stores/project";
  import { cn, initialOf } from "$lib/utils";

  let open = $state(false);
  let buttonEl: HTMLButtonElement | undefined = $state();

  const current = $derived(
    $projects.find((p) => p.slug === $activeProjectSlug) ?? $projects[0] ?? null,
  );

  function pick(slug: string) {
    activeProjectSlug.set(slug);
    open = false;
  }

  function handleOutsideClick(e: MouseEvent) {
    if (!open) return;
    if (buttonEl && !buttonEl.parentElement?.contains(e.target as Node)) {
      open = false;
    }
  }
</script>

<svelte:window onclick={handleOutsideClick} />

<div class="relative">
  <button
    bind:this={buttonEl}
    type="button"
    onclick={() => (open = !open)}
    class={cn(
      "flex w-full items-center gap-3 rounded-lg border bg-card p-2 text-left transition-colors",
      "hover:bg-accent",
      open && "ring-2 ring-ring ring-offset-2 ring-offset-background",
    )}
  >
    {#if current}
      <span class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md bg-primary/10 text-sm font-semibold text-primary">
        {initialOf(current.name)}
      </span>
      <span class="min-w-0 flex-1">
        <span class="block truncate text-sm font-medium leading-tight">{current.name}</span>
        <span class="block truncate text-xs text-muted-foreground">{current.slug}</span>
      </span>
    {:else}
      <span class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
        <FolderPlus class="h-4 w-4" />
      </span>
      <span class="min-w-0 flex-1 text-sm text-muted-foreground">No project yet</span>
    {/if}
    <ChevronsUpDown class="h-4 w-4 flex-shrink-0 text-muted-foreground" />
  </button>

  {#if open}
    <div class="absolute left-0 right-0 top-full z-30 mt-2 overflow-hidden rounded-lg border bg-popover bg-card shadow-lg">
      <div class="max-h-64 overflow-y-auto p-1">
        {#each $projects as p}
          <button
            type="button"
            onclick={() => pick(p.slug)}
            class={cn(
              "flex w-full items-center gap-3 rounded-md px-2 py-1.5 text-left text-sm transition-colors",
              "hover:bg-accent",
            )}
          >
            <span class="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md bg-primary/10 text-xs font-semibold text-primary">
              {initialOf(p.name)}
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate font-medium">{p.name}</span>
              <span class="block truncate text-xs text-muted-foreground">{p.slug}</span>
            </span>
            {#if p.slug === $activeProjectSlug}
              <Check class="h-4 w-4 flex-shrink-0 text-primary" />
            {/if}
          </button>
        {/each}
      </div>
      <div class="border-t p-1">
        <button
          type="button"
          onclick={() => { open = false; goto("/projects"); }}
          class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <FolderPlus class="h-4 w-4" />
          Manage projects
        </button>
      </div>
    </div>
  {/if}
</div>
