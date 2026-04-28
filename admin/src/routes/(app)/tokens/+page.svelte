<script lang="ts">
  import { onMount } from "svelte";
  import { Plus, Copy, Check, Trash2 } from "lucide-svelte";
  import { goto } from "$app/navigation";
  import { ApiError, api } from "$lib/api/client";
  import { user } from "$lib/stores/auth";
  import { projects } from "$lib/stores/project";
  import { toastError, toastSuccess } from "$lib/stores/toast";
  import Card from "$lib/components/ui/Card.svelte";
  import Button from "$lib/components/ui/Button.svelte";
  import Input from "$lib/components/ui/Input.svelte";
  import Label from "$lib/components/ui/Label.svelte";
  import Badge from "$lib/components/ui/Badge.svelte";
  import Sheet from "$lib/components/ui/Sheet.svelte";
  import Skeleton from "$lib/components/ui/Skeleton.svelte";
  import { fmtDate, fmtDateTime } from "$lib/utils";
  import type { Token, User } from "$lib/api/types";

  let users = $state<User[]>([]);
  let pickedUser = $state<string>("");
  let tokens = $state<Token[]>([]);
  let loading = $state(true);
  let openIssue = $state(false);
  let label = $state("");
  let scopeProject = $state<string>("");   // "" = all projects
  let saving = $state(false);
  let issued = $state<string | null>(null);
  let copied = $state(false);

  onMount(async () => {
    if ($user?.role !== "admin") { goto("/dashboard"); return; }
    try {
      users = await api.listUsers();
      pickedUser = users[0]?.id ?? "";
    } catch (err) { toastError(err instanceof ApiError ? err.message : "Failed to load"); }
    finally { loading = false; }
  });

  $effect(() => {
    const uid = pickedUser;
    if (!uid) { tokens = []; return; }
    (async () => {
      try { tokens = await api.listTokens(uid); }
      catch { tokens = []; }
    })();
  });

  async function issue(e: SubmitEvent) {
    e.preventDefault();
    if (!pickedUser) return;
    saving = true;
    try {
      const t = await api.issueToken(pickedUser, {
        label: label.trim() || undefined,
        project: scopeProject || undefined,
      });
      issued = t.token;
      tokens = await api.listTokens(pickedUser);
      label = ""; scopeProject = "";
      toastSuccess("Token issued. Copy it below.");
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Failed to issue token");
    } finally {
      saving = false;
    }
  }

  async function revoke(t: Token) {
    if (!confirm(`Revoke token "${t.label ?? t.id}"?`)) return;
    try {
      await api.revokeToken(t.id);
      tokens = await api.listTokens(pickedUser);
      toastSuccess("Revoked");
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Revoke failed");
    }
  }

  async function copyIssued() {
    if (!issued) return;
    try {
      await navigator.clipboard.writeText(issued);
      copied = true;
      setTimeout(() => (copied = false), 1500);
    } catch { /* ignore */ }
  }
</script>

<svelte:head><title>Tokens — Geshtu</title></svelte:head>

<header class="mb-6 flex items-center justify-between">
  <div>
    <h1 class="text-3xl font-semibold tracking-tight">Tokens</h1>
    <p class="mt-1 text-sm text-muted-foreground">
      Bearer tokens for MCP clients. Scope a token to one project to limit blast radius.
    </p>
  </div>
  <Button onclick={() => { openIssue = true; issued = null; }} disabled={!pickedUser}>
    <Plus class="h-4 w-4" /> Issue token
  </Button>
</header>

{#if loading}
  <Skeleton class="h-14 w-full" />
{:else if users.length === 0}
  <Card class="p-6 text-center text-sm text-muted-foreground">No users yet.</Card>
{:else}
  <Card class="mb-4 p-4">
    <Label for="u-pick">User</Label>
    <select
      id="u-pick"
      bind:value={pickedUser}
      class="mt-1.5 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
    >
      {#each users as u}
        <option value={u.id}>{u.display_name} &lt;{u.email}&gt; ({u.role})</option>
      {/each}
    </select>
  </Card>

  {#if tokens.length === 0}
    <Card class="p-6 text-center text-sm text-muted-foreground">No tokens for this user yet.</Card>
  {:else}
    <div class="space-y-2">
      {#each tokens as t}
        {@const revoked = !!t.revoked_at}
        <Card class="flex items-center gap-4 p-4 {revoked ? 'opacity-60' : ''}">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="font-medium">{t.label ?? "(unlabeled)"}</span>
              {#if revoked}
                <Badge variant="destructive">revoked</Badge>
              {:else if t.project_slug}
                <Badge variant="default">project: {t.project_slug}</Badge>
              {:else}
                <Badge variant="outline">all projects</Badge>
              {/if}
            </div>
            <div class="mt-1 text-xs text-muted-foreground">
              created {fmtDate(t.created_at)}
              {#if t.last_used_at} · last used {fmtDateTime(t.last_used_at)}{/if}
            </div>
          </div>
          {#if !revoked}
            <Button variant="ghost" size="icon" onclick={() => revoke(t)}>
              <Trash2 class="h-4 w-4" />
            </Button>
          {/if}
        </Card>
      {/each}
    </div>
  {/if}
{/if}

<Sheet bind:open={openIssue} title={issued ? "Token issued" : "Issue new token"}
       onClose={() => (issued = null)}>
  {#if issued}
    <div class="space-y-4">
      <div class="rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-sm">
        <strong>Copy the token now.</strong> It will not be shown again.
      </div>
      <div class="space-y-1.5">
        <Label>Token</Label>
        <div class="flex gap-2">
          <Input value={issued} class="font-mono" />
          <Button variant="outline" size="icon" onclick={copyIssued}>
            {#if copied}<Check class="h-4 w-4" />{:else}<Copy class="h-4 w-4" />{/if}
          </Button>
        </div>
      </div>
      <div class="flex justify-end pt-2">
        <Button onclick={() => { openIssue = false; issued = null; }}>Done</Button>
      </div>
    </div>
  {:else}
    <form class="space-y-4" onsubmit={issue}>
      <div class="space-y-1.5">
        <Label for="t-label">Label</Label>
        <Input id="t-label" placeholder="alice's laptop" bind:value={label} />
      </div>
      <div class="space-y-1.5">
        <Label for="t-scope">Scope</Label>
        <select
          id="t-scope"
          bind:value={scopeProject}
          class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="">All projects (admin pattern)</option>
          {#each $projects as p}
            <option value={p.slug}>{p.name} ({p.slug})</option>
          {/each}
        </select>
        <p class="text-xs text-muted-foreground">
          Scoped tokens fail with 403 if used against any other project.
        </p>
      </div>
      <div class="flex justify-end gap-2 pt-2">
        <Button variant="ghost" onclick={() => (openIssue = false)}>Cancel</Button>
        <Button type="submit" loading={saving}>Issue</Button>
      </div>
    </form>
  {/if}
</Sheet>
