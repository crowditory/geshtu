import { browser } from "$app/environment";
import { writable, get } from "svelte/store";

import type { User } from "$lib/api/types";

/**
 * Auth state lives in localStorage so it survives reloads. Two keys:
 *   geshtu:token       — the bearer string
 *   geshtu:user        — JSON-encoded User (for sidebar display before /me resolves)
 *
 * The store is the source of truth in-memory; localStorage is the source
 * of truth across reloads. We sync writes to both. We never put plaintext
 * tokens into HttpOnly cookies because we don't have a same-origin server
 * route to set them — admin is a static SPA. localStorage is the right
 * trade-off for a token bound to a specific user that we already trust.
 */

const TOKEN_KEY = "geshtu:token";
const USER_KEY = "geshtu:user";

function readToken(): string | null {
  if (!browser) return null;
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function readUser(): User | null {
  if (!browser) return null;
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

export const token = writable<string | null>(readToken());
export const user = writable<User | null>(readUser());

export function getToken(): string | null {
  return get(token);
}

export function getUser(): User | null {
  return get(user);
}

export function setSession(t: string, u: User): void {
  token.set(t);
  user.set(u);
  if (browser) {
    try {
      localStorage.setItem(TOKEN_KEY, t);
      localStorage.setItem(USER_KEY, JSON.stringify(u));
    } catch { /* ignore */ }
  }
}

export function setUser(u: User): void {
  user.set(u);
  if (browser) {
    try {
      localStorage.setItem(USER_KEY, JSON.stringify(u));
    } catch { /* ignore */ }
  }
}

export function clearSession(): void {
  token.set(null);
  user.set(null);
  if (browser) {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    } catch { /* ignore */ }
  }
}
