<script lang="ts">
  import { cn } from "$lib/utils";

  interface Props {
    variant?: "default" | "secondary" | "outline" | "success" | "destructive";
    class?: string;
    children?: import("svelte").Snippet;
  }
  let { variant = "default", class: cls = "", children }: Props = $props();

  const variantCls: Record<NonNullable<Props["variant"]>, string> = {
    default: "bg-primary/10 text-primary border-primary/20",
    secondary: "bg-secondary text-secondary-foreground border-transparent",
    outline: "border-border text-foreground",
    success: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
    destructive: "bg-destructive/10 text-destructive border-destructive/20",
  };
</script>

<span
  class={cn(
    "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
    variantCls[variant],
    cls,
  )}
>
  {@render children?.()}
</span>
