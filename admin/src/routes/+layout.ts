// SPA mode: no SSR anywhere. Admin is auth-gated, rendering on the server
// without a session has nothing useful to show.
export const ssr = false;
export const prerender = false;
export const trailingSlash = "ignore";
