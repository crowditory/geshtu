import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Tailwind class merger — same `cn()` helper shadcn projects use. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toISOString().slice(0, 10);
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toISOString().slice(0, 16).replace("T", " ");
}

export function initialOf(s: string): string {
  if (!s) return "?";
  return s.trim().charAt(0).toUpperCase();
}
