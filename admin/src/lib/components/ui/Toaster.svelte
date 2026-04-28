<script lang="ts">
  import { fly } from "svelte/transition";
  import { CheckCircle2, AlertTriangle, Info } from "lucide-svelte";
  import { toasts } from "$lib/stores/toast";
  import { cn } from "$lib/utils";
</script>

<div class="pointer-events-none fixed bottom-4 right-4 z-[60] flex flex-col gap-2">
  {#each $toasts as t (t.id)}
    <div
      transition:fly={{ y: 20, duration: 200 }}
      class={cn(
        "pointer-events-auto flex min-w-[260px] items-start gap-3 rounded-lg border bg-card px-4 py-3 text-sm shadow-md",
        t.kind === "error" && "border-destructive/40",
        t.kind === "success" && "border-emerald-500/40",
      )}
    >
      {#if t.kind === "success"}
        <CheckCircle2 class="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-500" />
      {:else if t.kind === "error"}
        <AlertTriangle class="mt-0.5 h-4 w-4 flex-shrink-0 text-destructive" />
      {:else}
        <Info class="mt-0.5 h-4 w-4 flex-shrink-0 text-primary" />
      {/if}
      <span class="leading-snug">{t.text}</span>
    </div>
  {/each}
</div>
