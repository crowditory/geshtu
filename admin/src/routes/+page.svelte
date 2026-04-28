<script lang="ts">
  // Welcome / landing — first thing an unauthed visitor sees. If a saved
  // session exists, hop straight to /dashboard so users don't see a flash
  // of the marketing card.
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { ArrowRight, Github, BookOpen } from "lucide-svelte";
  import Logo from "$lib/components/Logo.svelte";
  import Button from "$lib/components/ui/Button.svelte";
  import ThemeToggle from "$lib/components/ThemeToggle.svelte";
  import { getToken } from "$lib/stores/auth";

  onMount(() => {
    if (getToken()) goto("/dashboard");
  });
</script>

<svelte:head>
  <title>Geshtu — self-hosted shared memory for teams</title>
</svelte:head>

<div class="relative flex min-h-screen flex-col bg-background">
  <!-- subtle radial backdrop -->
  <div
    class="pointer-events-none absolute inset-0 -z-10 opacity-60"
    style="background:
      radial-gradient(circle at 20% 0%, hsl(var(--primary) / 0.06), transparent 50%),
      radial-gradient(circle at 80% 100%, hsl(var(--primary) / 0.04), transparent 60%);"
    aria-hidden="true"
  ></div>

  <!-- top bar -->
  <header class="flex items-center justify-between px-6 py-5">
    <div class="flex items-center gap-2">
      <Logo size="sm" />
      <span class="text-sm font-semibold">Geshtu</span>
    </div>
    <div class="flex items-center gap-2">
      <ThemeToggle />
      <a
        href="https://github.com/crowditory/geshtu"
        class="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        aria-label="GitHub"
      >
        <Github class="h-4 w-4" />
      </a>
    </div>
  </header>

  <!-- centered hero -->
  <main class="flex flex-1 items-center justify-center px-6">
    <div class="w-full max-w-xl text-center">
      <div class="mb-6 flex justify-center">
        <Logo size="lg" />
      </div>
      <h1 class="text-4xl font-semibold tracking-tight sm:text-5xl">
        Shared memory for teams using LLMs.
      </h1>
      <p class="mt-4 text-pretty text-base text-muted-foreground sm:text-lg">
        Capture facts and decisions from your conversations. Ask any teammate's
        LLM to catch up on the project — async, scoped, cited. Self-hosted.
      </p>

      <div class="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
        <Button href="/login" size="lg" class="w-full sm:w-auto">
          Sign in
          <ArrowRight class="h-4 w-4" />
        </Button>
        <Button
          href="https://github.com/crowditory/geshtu#readme"
          variant="outline"
          size="lg"
          class="w-full sm:w-auto"
        >
          <BookOpen class="h-4 w-4" />
          Documentation
        </Button>
      </div>

      <div class="mt-12 grid grid-cols-1 gap-4 text-left sm:grid-cols-3">
        <div class="rounded-lg border bg-card p-4">
          <div class="text-sm font-medium">Auto-extracted</div>
          <p class="mt-1 text-xs text-muted-foreground">
            Facts and decisions surface from chats via Claude Haiku.
          </p>
        </div>
        <div class="rounded-lg border bg-card p-4">
          <div class="text-sm font-medium">Project-scoped</div>
          <p class="mt-1 text-xs text-muted-foreground">
            Tokens can be tied to a single project. No cross-leaks.
          </p>
        </div>
        <div class="rounded-lg border bg-card p-4">
          <div class="text-sm font-medium">Async digests</div>
          <p class="mt-1 text-xs text-muted-foreground">
            Three depths from ~300 to ~2,500 words on demand.
          </p>
        </div>
      </div>
    </div>
  </main>

  <footer class="px-6 py-4 text-center text-xs text-muted-foreground">
    Self-hosted · AGPL-3.0 · Built by Crowditory
  </footer>
</div>
