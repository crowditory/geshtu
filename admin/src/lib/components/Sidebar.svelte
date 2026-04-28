<script lang="ts">
  import {
    LayoutDashboard,
    FolderKanban,
    Search,
    Lightbulb,
    FileText,
    Users as UsersIcon,
    KeyRound,
    LogOut,
    Plug,
  } from "lucide-svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import Logo from "./Logo.svelte";
  import ProjectSwitcher from "./ProjectSwitcher.svelte";
  import ThemeToggle from "./ThemeToggle.svelte";
  import { user, clearSession } from "$lib/stores/auth";
  import { cn, initialOf } from "$lib/utils";

  // Items are tabs in the left rail. Icon + label, with `admin: true` items
  // hidden for non-admin tokens.
  const items = [
    { href: "/dashboard",  label: "Dashboard", icon: LayoutDashboard },
    { href: "/connect",    label: "Connect",   icon: Plug },
    { href: "/projects",   label: "Projects",  icon: FolderKanban },
    { href: "/facts",      label: "Facts",     icon: Search },
    { href: "/decisions",  label: "Decisions", icon: Lightbulb },
    { href: "/digests",    label: "Digests",   icon: FileText },
    { href: "/users",      label: "Users",     icon: UsersIcon, admin: true },
    { href: "/tokens",     label: "Tokens",    icon: KeyRound, admin: true },
  ];

  const visibleItems = $derived(
    items.filter((it) => !it.admin || $user?.role === "admin"),
  );

  function isActive(href: string): boolean {
    return $page.url.pathname === href || $page.url.pathname.startsWith(href + "/");
  }

  function signOut() {
    clearSession();
    goto("/login");
  }
</script>

<aside class="flex h-screen w-64 flex-shrink-0 flex-col border-r bg-card/40">
  <!-- brand -->
  <div class="flex items-center gap-2 px-4 pt-5 pb-3">
    <Logo size="sm" />
    <div>
      <div class="text-sm font-semibold leading-tight">Geshtu</div>
      <div class="text-xs text-muted-foreground">Team memory</div>
    </div>
    <div class="ml-auto">
      <ThemeToggle />
    </div>
  </div>

  <!-- project switcher -->
  <div class="px-3 pb-3">
    <ProjectSwitcher />
  </div>

  <!-- tabs -->
  <nav class="flex-1 space-y-0.5 px-2 py-2">
    {#each visibleItems as it}
      {@const active = isActive(it.href)}
      <a
        href={it.href}
        class={cn(
          "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
          active
            ? "bg-primary/10 text-primary"
            : "text-muted-foreground hover:bg-accent hover:text-foreground",
        )}
      >
        {#if active}
          <span class="absolute inset-y-1 left-0 w-0.5 rounded-r-full bg-primary" aria-hidden="true"></span>
        {/if}
        <it.icon class={cn("h-4 w-4 flex-shrink-0", active ? "text-primary" : "")} />
        <span>{it.label}</span>
      </a>
    {/each}
  </nav>

  <!-- identity / signout -->
  <div class="mt-auto border-t p-3">
    {#if $user}
      <div class="flex items-center gap-3 rounded-lg p-2">
        <span class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
          {initialOf($user.display_name || $user.email)}
        </span>
        <div class="min-w-0 flex-1">
          <div class="truncate text-sm font-medium">{$user.display_name}</div>
          <div class="flex items-center gap-1.5 truncate text-xs text-muted-foreground">
            <span class="truncate">{$user.email}</span>
            <span class="rounded bg-muted px-1 py-0.5 text-[10px] uppercase tracking-wider">
              {$user.role}
            </span>
          </div>
        </div>
        <button
          type="button"
          onclick={signOut}
          class="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
          aria-label="Sign out"
          title="Sign out"
        >
          <LogOut class="h-4 w-4" />
        </button>
      </div>
    {/if}
  </div>
</aside>
