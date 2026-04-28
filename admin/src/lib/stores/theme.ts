import { browser } from "$app/environment";
import { writable } from "svelte/store";

type Theme = "light" | "dark";

function readTheme(): Theme {
  if (!browser) return "light";
  try {
    const saved = localStorage.getItem("geshtu:theme");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  } catch {
    return "light";
  }
}

export const theme = writable<Theme>(readTheme());

theme.subscribe((value) => {
  if (!browser) return;
  try {
    localStorage.setItem("geshtu:theme", value);
    document.documentElement.classList.toggle("dark", value === "dark");
  } catch { /* ignore */ }
});

export function toggleTheme(): void {
  theme.update((t) => (t === "dark" ? "light" : "dark"));
}
