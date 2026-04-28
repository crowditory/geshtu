<script lang="ts">
  import { cn } from "$lib/utils";
  interface Props { size?: "sm" | "md" | "lg"; class?: string; }
  let { size = "md", class: cls = "" }: Props = $props();
  const sizeCls = {
    sm: "h-7 w-7 text-sm",
    md: "h-9 w-9 text-base",
    lg: "h-12 w-12 text-xl",
  };
</script>

<div class={cn(
  "inline-flex items-center justify-center rounded-lg bg-primary font-bold text-primary-foreground shadow-sm",
  sizeCls[size],
  cls,
)}>
  G
</div>
