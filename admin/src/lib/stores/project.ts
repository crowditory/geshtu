import { browser } from "$app/environment";
import { writable } from "svelte/store";

import type { Project } from "$lib/api/types";

/**
 * The "active project" is a UI concept — it's the slug the sidebar shows
 * highlighted, and the default that pages plug into their queries. It
 * persists across reloads so coming back to /facts doesn't lose context.
 *
 * It's NOT enforced at API level — the API still goes by whatever each
 * route receives. This store only steers what the UI defaults to.
 */

const KEY = "geshtu:active-project";

function read(): string | null {
  if (!browser) return null;
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export const activeProjectSlug = writable<string | null>(read());
export const projects = writable<Project[]>([]);

activeProjectSlug.subscribe((slug) => {
  if (!browser) return;
  try {
    if (slug) localStorage.setItem(KEY, slug);
    else localStorage.removeItem(KEY);
  } catch { /* ignore */ }
});
