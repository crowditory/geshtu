import { writable } from "svelte/store";

export type ToastKind = "info" | "success" | "error";

export interface Toast {
  id: number;
  kind: ToastKind;
  text: string;
}

let nextId = 1;
export const toasts = writable<Toast[]>([]);

export function toast(text: string, kind: ToastKind = "info", ttlMs = 4000): void {
  const id = nextId++;
  toasts.update((arr) => [...arr, { id, kind, text }]);
  setTimeout(() => {
    toasts.update((arr) => arr.filter((t) => t.id !== id));
  }, ttlMs);
}

export const toastSuccess = (text: string) => toast(text, "success");
export const toastError = (text: string) => toast(text, "error");
