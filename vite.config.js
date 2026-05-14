import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "tailwindcss";

export default defineConfig(({ command }) => ({
  // Production builds are served by FastAPI's StaticFiles mount at /static/,
  // so the built assets live at /static/dist/assets/*.  The dev server uses
  // "/" so the /static proxy does not intercept Vite's own asset requests.
  base: command === "build" ? "/static/dist/" : "/",
  plugins: [vue()],
  root: "frontend/vue",
  css: {
    postcss: {
      plugins: [tailwindcss()]
    }
  },
  build: {
    outDir: "../static/dist",
    emptyOutDir: true,
    manifest: true
  },
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      "/api": "http://localhost:8000",
      "/auth": "http://localhost:8000",
      "/static": "http://localhost:8000"
    }
  }
}));
