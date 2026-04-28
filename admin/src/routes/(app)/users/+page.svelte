<script lang="ts">
  import { onMount } from "svelte";
  import { Plus, Copy, Check } from "lucide-svelte";
  import { goto } from "$app/navigation";
  import { ApiError, api } from "$lib/api/client";
  import { user } from "$lib/stores/auth";
  import { toastError, toastSuccess } from "$lib/stores/toast";
  import Card from "$lib/components/ui/Card.svelte";
  import Button from "$lib/components/ui/Button.svelte";
  import Input from "$lib/components/ui/Input.svelte";
  import Label from "$lib/components/ui/Label.svelte";
  import Badge from "$lib/components/ui/Badge.svelte";
  import Sheet from "$lib/components/ui/Sheet.svelte";
  import Skeleton from "$lib/components/ui/Skeleton.svelte";
  import { fmtDate, fmtDateTime, initialOf } from "$lib/utils";
  import type { User } from "$lib/api/types";

  let rows = $state<User[]>([]);
  let loading = $state(true);
  let openCreate = $state(false);
  let email = $state("");
  let displayName = $state("");
  let role = $state<"member" | "admin">("member");
  let saving = $state(false);
  let issuedToken = $state<string | null>(null);
  let copied = $state(false);

  onMount(async () => {
    if ($user?.role !== "admin") { goto("/dashboard"); return; }
    try { rows = await api.listUsers(); }
    catch (err) { toastError(err instanceof ApiError ? err.message : "Failed to load"); }
    finally { loading = false; }
  });

  async function create(e: SubmitEvent) {
    e.preventDefault();
    if (!email.trim() || !displayName.trim()) return;
    saving = true;
    try {
      const u = await api.createUser({ email: email.trim(), display_name: displayName.trim(), role });
      rows = [u, ...rows];
      issuedToken = u.token;
      toastSuccess("User created. Copy the token below before closing.");
      email = ""; displayName = ""; role = "member";
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Failed to create user");
    } finally {
      saving = false;
    }
  }

  async function copyToken() {
    if (!issuedToken) return;
    try {
      await navigator.clipboard.writeText(issuedToken);
      copied = true;
      setTimeout(() => (copied = false), 1500);
    } catch { /* ignore */ }
  }
</script>

<svelte:head><title>Users — Geshtu</title></svelte:head>

<header class="mb-6 flex items-center justify-between">
  <div>
    <h1 class="text-3xl font-semibold tracking-tight">Users</h1>
    <p class="mt-1 text-sm text-muted-foreground">Members of this Geshtu instance.</p>
  </div>
  <Button onclick={() => { openCreate = true; issuedToken = null; }}>
    <Plus class="h-4 w-4" /> Add user
  </Button>
</header>

{#if loading}
  <div class="space-y-3">
    <Skeleton class="h-14 w-full" />
    <Skeleton class="h-14 w-full" />
  </div>
{:else}
  <div class="space-y-2">
    {#each rows as u}
      <Card class="flex items-center gap-4 p-4">
        <span class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
          {initialOf(u.display_name)}
        </span>
        <div class="min-w-0 flex-1">
          <div class="font-medium">{u.display_name}</div>
          <div class="text-xs text-muted-foreground">{u.email}</div>
        </div>
        <Badge variant={u.role === "admin" ? "default" : "secondary"}>{u.role}</Badge>
        <div class="hidden text-right text-xs text-muted-foreground md:block">
          <div>created {fmtDate(u.created_at)}</div>
          <div>seen {fmtDateTime(u.last_seen_at)}</div>
        </div>
      </Card>
    {/each}
  </div>
{/if}

<Sheet bind:open={openCreate} title={issuedToken ? "User created" : "Add user"}
       onClose={() => (issuedToken = null)}>
  {#if issuedToken}
    <div class="space-y-4">
      <div class="rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-sm">
        <strong>Save this token now.</strong> It will not be shown again.
      </div>
      <div class="space-y-1.5">
        <Label>Token</Label>
        <div class="flex gap-2">
          <Input value={issuedToken} class="font-mono" />
          <Button variant="outline" size="icon" onclick={copyToken}>
            {#if copied}<Check class="h-4 w-4" />{:else}<Copy class="h-4 w-4" />{/if}
          </Button>
        </div>
      </div>
      <div class="flex justify-end pt-2">
        <Button onclick={() => { openCreate = false; issuedToken = null; }}>Done</Button>
      </div>
    </div>
  {:else}
    <form class="space-y-4" onsubmit={create}>
      <div class="space-y-1.5">
        <Label for="u-email">Email</Label>
        <Input id="u-email" type="email" required autocomplete="off" bind:value={email} />
      </div>
      <div class="space-y-1.5">
        <Label for="u-name">Display name</Label>
        <Input id="u-name" required bind:value={displayName} />
      </div>
      <div class="space-y-1.5">
        <Label for="u-role">Role</Label>
        <select
          id="u-role"
          bind:value={role}
          class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          <option value="member">Member</option>
          <option value="admin">Admin</option>
        </select>
      </div>
      <div class="flex justify-end gap-2 pt-2">
        <Button variant="ghost" onclick={() => (openCreate = false)}>Cancel</Button>
        <Button type="submit" loading={saving}>Create + issue token</Button>
      </div>
    </form>
  {/if}
</Sheet>
