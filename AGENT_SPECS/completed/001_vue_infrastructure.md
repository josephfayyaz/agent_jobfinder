# 001 Vue Infrastructure

## Goal

Add Vue 3 + Vite infrastructure to the existing project without changing the current Jinja, HTMX, Alpine, or backend behavior.

This task must only add the Vue app shell, Vite build setup, Vue Router, pinia, Tailwind integration, and one smoke-test page.

Do not migrate any existing page in this task.

## Project Context

Current frontend:

- FastAPI backend
- Jinja2 templates in `frontend/templates/`
- static JavaScript in `frontend/static/`
- Tailwind CSS
- HTMX
- Alpine.js

Vue migration target:

- Vue will gradually replace implemented pages later.
- FastAPI remains the backend.
- Existing backend services and business logic must stay unchanged.

## Hard Constraints

Do not modify business logic.

Do not modify these areas:

```text
job_agent/
start_apply/
config/
docs/
AGENT_SPECS/
temp_mac_test/
```

Do not modify or delete existing files in:

```text
frontend/templates/
frontend/static/
```

except `frontend/static/dist/` may be created by Vite build.

Do not convert any existing page to Vue.

Do not add a FastAPI SPA catch-all route.

Do not change existing `/ui/*` routes.

Do not add Docker.

Do not use TypeScript.

Do not switch from npm to yarn or pnpm.

## Dependencies

Use npm.

Install:

```bash
npm install vue vue-router pinia
npm install -D vite @vitejs/plugin-vue
```

`package-lock.json` must be updated.

## Files To Add

Add:

```text
frontend/vue/index.html
frontend/vue/src/main.js
frontend/vue/src/App.vue
frontend/vue/src/router/index.js
frontend/vue/src/layouts/AppLayout.vue
frontend/vue/src/pages/VueSmokePage.vue
frontend/vue/src/api/client.js
frontend/vue/src/assets/tailwind.css
vite.config.js
```

Modify only if needed:

```text
package.json
package-lock.json
tailwind.config.js
.gitignore
```

## package.json

Add these scripts without removing existing scripts:

```json
{
  "dev:vue": "vite --config vite.config.js",
  "build:vue": "vite build --config vite.config.js",
  "preview:vue": "vite preview --config vite.config.js"
}
```

## vite.config.js

Create `vite.config.js` at project root:

```js
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  root: "frontend/vue",
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
});
```

## frontend/vue/index.html

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Local LLM Job Agent</title>
  </head>
  <body class="bg-slate-50 text-slate-950">
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

## frontend/vue/src/main.js

```js
import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./assets/tailwind.css";

createApp(App).use(createPinia()).use(router).mount("#app");
```

## frontend/vue/src/App.vue

```vue
<script setup>
import AppLayout from "./layouts/AppLayout.vue";
</script>

<template>
  <AppLayout>
    <router-view />
  </AppLayout>
</template>
```

## frontend/vue/src/router/index.js

```js
import { createRouter, createWebHistory } from "vue-router";
import VueSmokePage from "../pages/VueSmokePage.vue";

const routes = [
  {
    path: "/vue-smoke",
    name: "vue-smoke",
    component: VueSmokePage
  },
  {
    path: "/",
    redirect: "/vue-smoke"
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;
```

## frontend/vue/src/layouts/AppLayout.vue

```vue
<template>
  <div class="min-h-screen bg-slate-50 text-slate-950">
    <header class="border-b border-slate-200 bg-white">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <div>
          <p class="text-sm font-medium text-slate-500">Local LLM Job Agent</p>
          <h1 class="text-xl font-semibold tracking-tight">Vue Frontend Shell</h1>
        </div>

        <nav class="flex items-center gap-4 text-sm">
          <RouterLink
            to="/vue-smoke"
            class="font-medium text-slate-700 hover:text-slate-950"
          >
            Vue Smoke
          </RouterLink>
        </nav>
      </div>
    </header>

    <main class="mx-auto max-w-6xl px-6 py-8">
      <slot />
    </main>
  </div>
</template>
```

## frontend/vue/src/pages/VueSmokePage.vue

```vue
<script setup>
import { ref } from "vue";

const count = ref(0);
</script>

<template>
  <section class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <div class="max-w-2xl">
      <p class="text-sm font-medium text-emerald-700">Vue is mounted</p>

      <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        Vue infrastructure smoke test
      </h2>

      <p class="mt-3 text-sm leading-6 text-slate-600">
        This page confirms that Vue 3, Vue Router, pinia, Vite, and Tailwind are wired
        without replacing the existing Jinja frontend.
      </p>

      <button
        type="button"
        class="mt-6 rounded-xl bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        @click="count += 1"
      >
        Clicked {{ count }} times
      </button>
    </div>
  </section>
</template>
```

## frontend/vue/src/api/client.js

```js
export async function apiFetch(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  const contentType = response.headers.get("content-type") || "";

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    if (contentType.includes("application/json")) {
      const payload = await response.json();
      message = payload.detail || payload.message || message;
    } else {
      const text = await response.text();
      message = text || message;
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response.text();
}
```

## frontend/vue/src/assets/tailwind.css

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

## tailwind.config.js

Add these paths to the existing `content` array:

```js
"./frontend/vue/index.html",
"./frontend/vue/src/**/*.{vue,js}"
```

Do not remove existing paths for:

```text
frontend/templates/
frontend/static/
```

## .gitignore

Add this if not already present:

```gitignore
frontend/static/dist/
```

Do not ignore:

```text
frontend/vue/
vite.config.js
package-lock.json
```

## Validation Commands

Run:

```bash
npm install
npm run build:vue
```

Then run:

```bash
pytest
```

If `pytest` fails because of unrelated existing issues, report the exact error.

Also run any existing frontend build command if it exists in `package.json`.

## Manual Validation

Run:

```bash
npm run dev:vue
```

Open:

```text
http://localhost:5173/vue-smoke
```

Expected:

- page loads
- no console errors
- Tailwind styles apply
- button click increments count
- existing Jinja frontend still works
- no `/ui/*` route changed

## Acceptance Criteria

The task is complete only if:

1. Vue 3 is installed.
2. Vite is installed.
3. Vue Router is installed.
4. pinia is installed.
5. Vue app exists under `frontend/vue/`.
6. `npm run build:vue` succeeds.
7. Tailwind works in Vue components.
8. `/vue-smoke` works in Vite dev server.
9. Existing Jinja frontend is untouched.
10. No existing page is migrated.
11. No backend business logic is modified.
12. `package-lock.json` is updated.

## Forbidden Outcomes

Do not:

- convert Jinja templates
- delete `frontend/templates/`
- delete `frontend/static/*.js`
- remove HTMX or Alpine
- change backend business logic
- change LLM provider logic
- change CV generation logic
- add FastAPI SPA catch-all route
- break `/ui/*` routes
- create Vue project outside `frontend/vue`
- use Nuxt
- use TypeScript
- switch package manager
- add Docker

## Final Codex Response

Report:

1. files added
2. files modified
3. commands run
4. build result
5. test result
6. manual validation result
7. known issues

Do not continue to page migration.
