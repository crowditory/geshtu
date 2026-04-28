import adapter from "@sveltejs/adapter-static";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    // Static SPA: no Node runtime on prod, sirv just serves the build dir.
    // fallback: index.html → SvelteKit SPA mode (client-side routing for
    // every URL the static server doesn't have a file for).
    adapter: adapter({
      pages: "build",
      assets: "build",
      fallback: "index.html",
      precompress: false,
      strict: true,
    }),
    // No SSR anywhere — admin is auth-gated, server rendering with no
    // session has nothing to render. Set in +layout.ts as well, this is
    // belt-and-suspenders.
  },
};

export default config;
