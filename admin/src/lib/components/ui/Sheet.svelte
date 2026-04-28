<script lang="ts">
  import { fade, fly } from "svelte/transition";
  import { cn } from "$lib/utils";
  import { X } from "lucide-svelte";

  interface Props {
    open: boolean;
    title?: string;
    description?: string;
    side?: "right" | "left";
    class?: string;
    children?: import("svelte").Snippet;
    onClose?: () => void;
  }

  let {
    open = $bindable(false),
    title,
    description,
    side = "right",
    class: cls = "",
    children,
    onClose,
  }: Props = $props();

  function close() {
    open = false;
    onClose?.();
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === "Escape" && open) close();
  }
</script>

<svelte:window onkeydown={onKey} />

{#if open}
  <!-- Backdrop -->
  <div
    transition:fade={{ duration: 150 }}
    class="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm"
    onclick={close}
    role="presentation"
  ></div>

  <!-- Panel -->
  <aside
    transition:fly={{
      x: side === "right" ? 400 : -400,
      duration: 200,
      opacity: 1,
    }}
    class={cn(
      "fixed top-0 z-50 flex h-full w-full max-w-md flex-col gap-4 border-l bg-background p-6 shadow-lg",
      side === "right" ? "right-0" : "left-0",
      cls,
    )}
    aria-modal="true"
    role="dialog"
  >
    <header class="flex items-start justify-between">
      <div>
        {#if title}<h2 class="text-lg font-semibold">{title}</h2>{/if}
        {#if description}<p class="mt-1 text-sm text-muted-foreground">{description}</p>{/if}
      </div>
      <button
        type="button"
        onclick={close}
        class="rounded-md p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        aria-label="Close"
      >
        <X class="h-4 w-4" />
      </button>
    </header>
    <div class="flex-1 overflow-y-auto">
      {@render children?.()}
    </div>
  </aside>
{/if}
