<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import Sidebar from "$lib/components/Sidebar.svelte";
  import { ApiError, api } from "$lib/api/client";
  import { getToken, setUser, clearSession } from "$lib/stores/auth";
  import { activeProjectSlug, projects } from "$lib/stores/project";
  import { toastError } from "$lib/stores/toast";

  let { children } = $props();
  let ready = $state(false);

  onMount(async () => {
    const tok = getToken();
    if (!tok) {
      goto("/login");
      return;
    }
    try {
      // Validate the saved token + refresh user info on every reload.
      const me = await api.me();
      setUser(me);

      // Fetch projects so the switcher has data; default the active project
      // to the first one if nothing is selected yet.
      const list = await api.listProjects();
      projects.set(list);
      activeProjectSlug.update((cur) => {
        if (cur && list.some((p) => p.slug === cur)) return cur;
        return list[0]?.slug ?? null;
      });

      ready = true;
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        clearSession();
        goto("/login");
      } else {
        toastError(err instanceof Error ? err.message : "Failed to load");
      }
    }
  });
</script>

{#if ready}
  <div class="flex min-h-screen bg-background text-foreground">
    <Sidebar />
    <main class="flex-1 overflow-y-auto">
      <div class="mx-auto max-w-6xl px-8 py-8">
        {@render children?.()}
      </div>
    </main>
  </div>
{:else}
  <div class="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
    Loading…
  </div>
{/if}
