<script lang="ts">
  import { cn } from "$lib/utils";

  interface Props {
    for?: string;
    class?: string;
    children?: import("svelte").Snippet;
  }
  let { for: htmlFor, class: cls = "", children }: Props = $props();
</script>

<label
  for={htmlFor}
  class={cn("text-sm font-medium leading-none", cls)}
>
  {@render children?.()}
</label>
