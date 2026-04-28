<script lang="ts">
  import { cn } from "$lib/utils";
  interface Props { class?: string; }
  let { class: cls = "" }: Props = $props();
</script>

<div class={cn("animate-pulse rounded-md bg-muted", cls)}></div>
