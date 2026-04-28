<script lang="ts">
  import { Moon, Sun } from "lucide-svelte";
  import { theme, toggleTheme } from "$lib/stores/theme";
</script>

<button
  type="button"
  onclick={toggleTheme}
  class="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
  aria-label="Toggle theme"
>
  {#if $theme === "dark"}
    <Sun class="h-4 w-4" />
  {:else}
    <Moon class="h-4 w-4" />
  {/if}
</button>
