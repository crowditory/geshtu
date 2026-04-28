<script lang="ts">
  import { cn } from "$lib/utils";

  interface Props {
    variant?: "primary" | "secondary" | "ghost" | "outline" | "destructive";
    size?: "sm" | "md" | "lg" | "icon";
    type?: "button" | "submit" | "reset";
    disabled?: boolean;
    loading?: boolean;
    href?: string;
    class?: string;
    children?: import("svelte").Snippet;
    onclick?: (e: MouseEvent) => void;
  }

  let {
    variant = "primary",
    size = "md",
    type = "button",
    disabled = false,
    loading = false,
    href,
    class: cls = "",
    children,
    onclick,
  }: Props = $props();

  const variantCls: Record<NonNullable<Props["variant"]>, string> = {
    primary: "bg-primary text-primary-foreground hover:bg-primary/90",
    secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
    ghost: "hover:bg-accent hover:text-accent-foreground",
    outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
    destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
  };

  const sizeCls: Record<NonNullable<Props["size"]>, string> = {
    sm: "h-8 px-3 text-sm rounded-md",
    md: "h-10 px-4 text-sm rounded-md",
    lg: "h-11 px-6 text-base rounded-md",
    icon: "h-9 w-9 rounded-md",
  };

  const base =
    "inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium transition-colors " +
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 " +
    "focus-visible:ring-offset-background " +
    "disabled:pointer-events-none disabled:opacity-50";
</script>

{#if href}
  <a {href} class={cn(base, variantCls[variant], sizeCls[size], cls)}>
    {@render children?.()}
  </a>
{:else}
  <button
    {type}
    disabled={disabled || loading}
    class={cn(base, variantCls[variant], sizeCls[size], cls)}
    {onclick}
  >
    {#if loading}
      <span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden="true"></span>
    {/if}
    {@render children?.()}
  </button>
{/if}
