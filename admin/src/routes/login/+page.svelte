<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { Eye, EyeOff, KeyRound, ExternalLink } from "lucide-svelte";
  import { ApiError, api } from "$lib/api/client";
  import { getToken, setSession } from "$lib/stores/auth";
  import { toastError } from "$lib/stores/toast";
  import Button from "$lib/components/ui/Button.svelte";
  import Card from "$lib/components/ui/Card.svelte";
  import Input from "$lib/components/ui/Input.svelte";
  import Label from "$lib/components/ui/Label.svelte";
  import Logo from "$lib/components/Logo.svelte";
  import ThemeToggle from "$lib/components/ThemeToggle.svelte";

  let token = $state("");
  let expectedEmail = $state("");
  let showToken = $state(false);
  let submitting = $state(false);
  let error = $state<string | null>(null);

  onMount(() => {
    if (getToken()) goto("/dashboard");
  });

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    error = null;
    if (!token.trim()) {
      error = "Paste your token to continue.";
      return;
    }
    submitting = true;
    try {
      const me = await api.me(token.trim());
      // Optional belt-and-suspenders: if the operator filled in the
      // "expected email" field, refuse if the token identifies someone else.
      const expected = expectedEmail.trim().toLowerCase();
      if (
        expected &&
        me.email.toLowerCase() !== expected &&
        me.display_name.toLowerCase() !== expected
      ) {
        error = `This token belongs to ${me.email}, not ${expectedEmail}.`;
        return;
      }
      setSession(token.trim(), me);
      goto("/dashboard");
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 401) {
        error = "Token rejected. Check that it hasn't been revoked.";
      } else if (err instanceof Error) {
        error = err.message;
      } else {
        error = "Sign-in failed.";
      }
      toastError(error);
    } finally {
      submitting = false;
    }
  }
</script>

<svelte:head>
  <title>Sign in — Geshtu</title>
</svelte:head>

<div class="relative flex min-h-screen items-center justify-center bg-background px-6 py-10">
  <!-- soft backdrop -->
  <div
    class="pointer-events-none absolute inset-0 -z-10 opacity-50"
    style="background:
      radial-gradient(circle at 50% 30%, hsl(var(--primary) / 0.08), transparent 55%);"
    aria-hidden="true"
  ></div>

  <div class="absolute right-6 top-6">
    <ThemeToggle />
  </div>

  <Card class="w-full max-w-md p-8">
    <div class="flex flex-col items-center text-center">
      <Logo size="lg" />
      <h1 class="mt-5 text-2xl font-semibold tracking-tight">Sign in to Geshtu</h1>
      <p class="mt-1.5 text-sm text-muted-foreground">
        Paste the token your admin issued for you.
      </p>
    </div>

    <form class="mt-8 space-y-4" onsubmit={submit}>
      <div class="space-y-1.5">
        <Label for="email">Your email <span class="text-muted-foreground">(optional)</span></Label>
        <Input
          id="email"
          type="email"
          placeholder="alice@example.com"
          autocomplete="username"
          bind:value={expectedEmail}
        />
        <p class="text-xs text-muted-foreground">
          If filled, sign-in fails when the token belongs to someone else.
          Catches accidental copy-paste mistakes.
        </p>
      </div>

      <div class="space-y-1.5">
        <Label for="token">Access token</Label>
        <div class="relative">
          <Input
            id="token"
            type={showToken ? "text" : "password"}
            placeholder="tk_…"
            autocomplete="current-password"
            required
            class="pr-10 font-mono"
            bind:value={token}
          />
          <button
            type="button"
            onclick={() => (showToken = !showToken)}
            class="absolute right-1 top-1 inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
            aria-label={showToken ? "Hide token" : "Show token"}
          >
            {#if showToken}
              <EyeOff class="h-4 w-4" />
            {:else}
              <Eye class="h-4 w-4" />
            {/if}
          </button>
        </div>
      </div>

      {#if error}
        <div class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      {/if}

      <Button type="submit" size="lg" class="w-full" loading={submitting} disabled={submitting}>
        <KeyRound class="h-4 w-4" />
        Sign in
      </Button>
    </form>

    <div class="mt-6 flex items-center justify-between text-xs text-muted-foreground">
      <a href="/" class="hover:text-foreground">← Back</a>
      <a
        href="https://github.com/crowditory/geshtu/blob/main/docs/claude-desktop-setup.md"
        class="inline-flex items-center gap-1 hover:text-foreground"
      >
        How do I get a token?
        <ExternalLink class="h-3 w-3" />
      </a>
    </div>
  </Card>
</div>
