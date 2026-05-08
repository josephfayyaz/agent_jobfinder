# 002 Vue Layout and Router

## Goal

Create the real Vue application layout and route skeleton for all existing implemented pages, without migrating page logic yet.

This task must convert the current navigation/page map into Vue route placeholders and shared layout components.

Do not migrate existing page behavior in this task.

Do not remove existing Jinja templates, HTMX, Alpine, static JS, or backend `/ui/*` routes.

---

## Current Project State

Vue infrastructure already exists from:

```text
AGENT_SPECS/completed/001_vue_infrastructure.md
```

Expected existing Vue files:

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

Current legacy frontend pages exist under:

```text
frontend/templates/
frontend/static/
```

The Vue app should gradually replace those pages later.

This task only prepares:

- shared layout
- sidebar/header shell
- route skeletons
- placeholder pages
- setup route grouping
- navigation structure

---

## Hard Constraints

Do not modify backend business logic.

Do not modify:

```text
job_agent/
start_apply/
config/
docs/
temp_mac_test/
```

Do not delete or rewrite existing files in:

```text
frontend/templates/
frontend/static/
```

Do not migrate any existing page behavior.

Do not add API endpoints.

Do not add FastAPI SPA catch-all route.

Do not change existing `/ui/*` routes.

Do not change LLM provider logic.

Do not change CV generation logic.

Do not change verified-fact validation logic.

Do not change human approval workflow.

Do not add Docker.

Do not use TypeScript.

Do not switch package manager.

Use Vue 3, Vue Router, Pinia, Vite, and Tailwind only.

---

## Files To Add

Add these files:

```text
frontend/vue/src/components/AppSidebar.vue
frontend/vue/src/components/AppTopbar.vue
frontend/vue/src/components/AppPageHeader.vue
frontend/vue/src/components/PlaceholderPage.vue
frontend/vue/src/constants/navigation.js
frontend/vue/src/stores/setup.js
frontend/vue/src/pages/AboutPage.vue
frontend/vue/src/pages/AnalyticsPage.vue
frontend/vue/src/pages/ApplicationsPage.vue
frontend/vue/src/pages/ApplyPage.vue
frontend/vue/src/pages/CompaniesPage.vue
frontend/vue/src/pages/DashboardPage.vue
frontend/vue/src/pages/DraftDetailPage.vue
frontend/vue/src/pages/DraftsPage.vue
frontend/vue/src/pages/HelpPage.vue
frontend/vue/src/pages/JobsPage.vue
frontend/vue/src/pages/OfferCompassPage.vue
frontend/vue/src/pages/OnboardingPage.vue
frontend/vue/src/pages/SettingsPage.vue
frontend/vue/src/pages/SetupRequiredPage.vue
frontend/vue/src/pages/StoryBankPage.vue
frontend/vue/src/pages/ThesisPage.vue
frontend/vue/src/pages/VerifiedFactsPage.vue
frontend/vue/src/pages/WorkspaceResetPage.vue
frontend/vue/src/pages/NotFoundPage.vue
```

Modify these existing Vue files only:

```text
frontend/vue/src/App.vue
frontend/vue/src/router/index.js
frontend/vue/src/layouts/AppLayout.vue
frontend/vue/src/pages/VueSmokePage.vue
```

Modify `package.json` only if needed for scripts, but no dependency changes should be necessary.

Do not modify `frontend/templates/` or `frontend/static/` in this task.

---

## Route Map

Update Vue Router to include route placeholders for all implemented legacy pages.

Required routes:

```text
/                           -> redirect to /dashboard
/vue-smoke                  -> VueSmokePage
/dashboard                  -> DashboardPage
/jobs                       -> JobsPage
/companies                  -> CompaniesPage
/apply                      -> ApplyPage
/applications               -> ApplicationsPage
/drafts                     -> DraftsPage
/drafts/:id                 -> DraftDetailPage
/onboarding                 -> OnboardingPage
/settings                   -> SettingsPage
/setup-required             -> SetupRequiredPage
/verified-facts             -> VerifiedFactsPage
/story-bank                 -> StoryBankPage
/offer-compass              -> OfferCompassPage
/analytics                  -> AnalyticsPage
/thesis                     -> ThesisPage
/workspace-reset            -> WorkspaceResetPage
/help                       -> HelpPage
/about                      -> AboutPage
/:pathMatch(.*)*            -> NotFoundPage
```

Do not point Vue routes to old Jinja routes.

These are Vue frontend routes only.

---

## Navigation Groups

Create navigation groups that match the product areas.

Use this grouping:

```text
Main
- Dashboard: /dashboard
- Jobs: /jobs
- Companies: /companies
- Apply: /apply
- Applications: /applications
- Drafts: /drafts

Profile
- Onboarding: /onboarding
- Verified Facts: /verified-facts
- Settings: /settings

Career Tools
- Story Bank: /story-bank
- Offer Compass: /offer-compass
- Thesis: /thesis
- Analytics: /analytics

Workspace
- Workspace Reset: /workspace-reset
- Help: /help
- About: /about

Dev
- Vue Smoke: /vue-smoke
```

---

## frontend/vue/src/constants/navigation.js

Create:

```js
export const navigationGroups = [
  {
    label: "Main",
    items: [
      { label: "Dashboard", to: "/dashboard" },
      { label: "Jobs", to: "/jobs" },
      { label: "Companies", to: "/companies" },
      { label: "Apply", to: "/apply" },
      { label: "Applications", to: "/applications" },
      { label: "Drafts", to: "/drafts" }
    ]
  },
  {
    label: "Profile",
    items: [
      { label: "Onboarding", to: "/onboarding" },
      { label: "Verified Facts", to: "/verified-facts" },
      { label: "Settings", to: "/settings" }
    ]
  },
  {
    label: "Career Tools",
    items: [
      { label: "Story Bank", to: "/story-bank" },
      { label: "Offer Compass", to: "/offer-compass" },
      { label: "Thesis", to: "/thesis" },
      { label: "Analytics", to: "/analytics" }
    ]
  },
  {
    label: "Workspace",
    items: [
      { label: "Workspace Reset", to: "/workspace-reset" },
      { label: "Help", to: "/help" },
      { label: "About", to: "/about" }
    ]
  },
  {
    label: "Dev",
    items: [
      { label: "Vue Smoke", to: "/vue-smoke" }
    ]
  }
];
```

Do not add icons in this task unless already available without adding dependencies.

---

## frontend/vue/src/stores/setup.js

Create a Pinia setup store.

This store is a frontend-only placeholder for now.

Do not call backend APIs in this task.

Create:

```js
import { defineStore } from "pinia";

export const useSetupStore = defineStore("setup", {
  state: () => ({
    loaded: true,
    setupComplete: true,
    providerConfigured: true
  }),

  getters: {
    requiresSetup: (state) => !state.setupComplete || !state.providerConfigured
  },

  actions: {
    markLoaded() {
      this.loaded = true;
    }
  }
});
```

Important:

- This is temporary.
- Do not add API calls yet.
- Do not enforce setup gating yet.
- Real setup gating will be added in a later spec after API contracts are defined.

---

## frontend/vue/src/components/PlaceholderPage.vue

Create a reusable placeholder component.

Required props:

```text
title: string
description: string
legacyTemplate: string
legacyScript: string optional
status: string optional
```

Create:

```vue
<script setup>
defineProps({
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    required: true
  },
  legacyTemplate: {
    type: String,
    required: true
  },
  legacyScript: {
    type: String,
    default: ""
  },
  status: {
    type: String,
    default: "Route placeholder only"
  }
});
</script>

<template>
  <section class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
      <div>
        <p class="text-sm font-medium text-slate-500">{{ status }}</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
          {{ title }}
        </h2>
        <p class="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
          {{ description }}
        </p>
      </div>

      <div class="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        Not migrated yet
      </div>
    </div>

    <dl class="mt-6 grid gap-4 rounded-xl bg-slate-50 p-4 text-sm md:grid-cols-2">
      <div>
        <dt class="font-medium text-slate-500">Legacy template</dt>
        <dd class="mt-1 font-mono text-slate-900">{{ legacyTemplate }}</dd>
      </div>

      <div>
        <dt class="font-medium text-slate-500">Legacy script</dt>
        <dd class="mt-1 font-mono text-slate-900">
          {{ legacyScript || "None / unknown" }}
        </dd>
      </div>
    </dl>
  </section>
</template>
```

---

## frontend/vue/src/components/AppPageHeader.vue

Create:

```vue
<script setup>
defineProps({
  title: {
    type: String,
    required: true
  },
  eyebrow: {
    type: String,
    default: "Local LLM Job Agent"
  },
  description: {
    type: String,
    default: ""
  }
});
</script>

<template>
  <div class="mb-6">
    <p class="text-sm font-medium text-slate-500">{{ eyebrow }}</p>
    <h1 class="mt-1 text-3xl font-semibold tracking-tight text-slate-950">
      {{ title }}
    </h1>
    <p v-if="description" class="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
      {{ description }}
    </p>
  </div>
</template>
```

---

## frontend/vue/src/components/AppTopbar.vue

Create:

```vue
<template>
  <header class="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
    <div class="flex h-16 items-center justify-between px-6">
      <div>
        <p class="text-sm font-medium text-slate-500">Local-first job search + CV optimization</p>
        <h1 class="text-base font-semibold tracking-tight text-slate-950">
          Local LLM Job Agent
        </h1>
      </div>

      <div class="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
        Vue shell
      </div>
    </div>
  </header>
</template>
```

---

## frontend/vue/src/components/AppSidebar.vue

Create:

```vue
<script setup>
import { navigationGroups } from "../constants/navigation";
</script>

<template>
  <aside class="hidden min-h-screen w-72 shrink-0 border-r border-slate-200 bg-slate-950 text-white lg:block">
    <div class="px-6 py-6">
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
        Agent Jobfinder
      </p>
      <h2 class="mt-2 text-lg font-semibold">Vue Migration</h2>
    </div>

    <nav class="space-y-6 px-4 pb-8">
      <section v-for="group in navigationGroups" :key="group.label">
        <h3 class="px-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          {{ group.label }}
        </h3>

        <div class="mt-2 space-y-1">
          <RouterLink
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            class="block rounded-xl px-3 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white"
            active-class="bg-slate-800 text-white"
          >
            {{ item.label }}
          </RouterLink>
        </div>
      </section>
    </nav>
  </aside>
</template>
```

---

## frontend/vue/src/layouts/AppLayout.vue

Replace the current smoke-test-only layout with the real app shell.

Required implementation:

```vue
<script setup>
import AppSidebar from "../components/AppSidebar.vue";
import AppTopbar from "../components/AppTopbar.vue";
</script>

<template>
  <div class="min-h-screen bg-slate-50 text-slate-950">
    <div class="flex min-h-screen">
      <AppSidebar />

      <div class="flex min-w-0 flex-1 flex-col">
        <AppTopbar />

        <main class="flex-1 px-6 py-8">
          <div class="mx-auto max-w-7xl">
            <slot />
          </div>
        </main>
      </div>
    </div>
  </div>
</template>
```

---

## Page Placeholders

Each page file must import `PlaceholderPage` and render it with accurate metadata.

### Required page file pattern

Example:

```vue
<script setup>
import PlaceholderPage from "../components/PlaceholderPage.vue";
</script>

<template>
  <PlaceholderPage
    title="Dashboard"
    description="Vue route placeholder for the dashboard page. The existing Jinja implementation remains active until this page is migrated in a later spec."
    legacy-template="frontend/templates/dashboard.html"
    legacy-script="None / page behavior may be inline or backend-rendered"
  />
</template>
```

Use kebab-case attributes in templates, for example `legacy-template`.

---

## Exact Page Metadata

Create the following page files with these exact values.

### DashboardPage.vue

```text
title: Dashboard
legacyTemplate: frontend/templates/dashboard.html
legacyScript: None / page behavior may be inline or backend-rendered
description: Vue route placeholder for the dashboard page. The existing Jinja implementation remains active until this page is migrated in a later spec.
```

### JobsPage.vue

```text
title: Jobs
legacyTemplate: frontend/templates/jobs.html
legacyScript: frontend/static/jobs.js
description: Vue route placeholder for the jobs page. Job discovery and listing behavior will be migrated later after API contracts are defined.
```

### CompaniesPage.vue

```text
title: Companies
legacyTemplate: frontend/templates/companies.html
legacyScript: frontend/static/companies.js
description: Vue route placeholder for the companies page. Company research behavior will be migrated later after API contracts are defined.
```

### ApplyPage.vue

```text
title: Apply
legacyTemplate: frontend/templates/apply.html
legacyScript: frontend/static/apply.js
description: Vue route placeholder for the apply flow. Paste JD, scoring, clarifying questions, and draft generation remain in the existing implementation until migrated later.
```

### ApplicationsPage.vue

```text
title: Applications
legacyTemplate: frontend/templates/applications.html
legacyScript: None / page behavior may be inline or backend-rendered
description: Vue route placeholder for the applications page. Application tracking behavior remains in the existing implementation until migrated later.
```

### DraftsPage.vue

```text
title: Drafts
legacyTemplate: frontend/templates/drafts.html
legacyScript: None / page behavior may be inline or backend-rendered
description: Vue route placeholder for the drafts list. Draft review and revision behavior remains in the existing implementation until migrated later.
```

### DraftDetailPage.vue

This page must read route param `id` and show it in the description.

Implementation:

```vue
<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import PlaceholderPage from "../components/PlaceholderPage.vue";

const route = useRoute();
const draftId = computed(() => route.params.id);
</script>

<template>
  <PlaceholderPage
    title="Draft Detail"
    :description="`Vue route placeholder for draft detail ID ${draftId}. Draft review, revise, polish, and human approval behavior remains in the existing implementation until migrated later.`"
    legacy-template="frontend/templates/draft_detail.html"
    legacy-script="frontend/static/draft_detail.js"
  />
</template>
```

### OnboardingPage.vue

```text
title: Onboarding
legacyTemplate: frontend/templates/onboarding.html
legacyScript: frontend/static/onboarding.js
description: Vue route placeholder for the onboarding wizard. Provider selection, profile intake, verified facts, Q&A, review, and setup gating remain in the existing implementation until migrated later.
```

### SettingsPage.vue

```text
title: Settings
legacyTemplate: frontend/templates/settings.html
legacyScript: frontend/static/settings.js
description: Vue route placeholder for settings. Provider configuration, local model settings, and system keyring behavior remain in the existing implementation until migrated later.
```

### SetupRequiredPage.vue

```text
title: Setup Required
legacyTemplate: frontend/templates/setup_required.html
legacyScript: None / page behavior may be inline or backend-rendered
description: Vue route placeholder for setup-required gating. Real setup gating must remain backend-controlled until migrated later.
```

### VerifiedFactsPage.vue

```text
title: Verified Facts
legacyTemplate: frontend/templates/verified_facts.html
legacyScript: frontend/static/verified_facts.js
description: Vue route placeholder for verified facts. Fact traceability and validation remain backend-controlled and must not be reimplemented in this task.
```

### StoryBankPage.vue

```text
title: Story Bank
legacyTemplate: frontend/templates/story_bank.html
legacyScript: None / page behavior may be inline or backend-rendered
description: Vue route placeholder for STAR narratives and reusable candidate stories. Existing behavior remains active until migrated later.
```

### OfferCompassPage.vue

```text
title: Offer Compass
legacyTemplate: frontend/templates/offer_compass.html
legacyScript: None / page behavior may be inline or backend-rendered
description: Vue route placeholder for offer comparison. Existing behavior remains active until migrated later.
```

### AnalyticsPage.vue

```text
title: Analytics
legacyTemplate: frontend/templates/analytics.html
legacyScript: None / page behavior may be inline or backend-rendered
description: Vue route placeholder for analytics. Rejection patterns, skill gaps, hiring velocity, and market intelligence remain in the existing implementation until migrated later.
```

### ThesisPage.vue

```text
title: Thesis
legacyTemplate: frontend/templates/thesis.html
legacyScript: None / page behavior may be inline or backend-rendered
description: Vue route placeholder for thesis and traineeship targeting. Existing behavior remains active until migrated later.
```

### WorkspaceResetPage.vue

```text
title: Workspace Reset
legacyTemplate: frontend/templates/workspace_reset.html
legacyScript: frontend/static/workspace_reset.js
description: Vue route placeholder for workspace backup, reset, and delete flows. Existing behavior remains active until migrated later.
```

### HelpPage.vue

```text
title: Help
legacyTemplate: frontend/templates/help.html
legacyScript: None / page behavior may be inline or backend-rendered
description: Vue route placeholder for help content. Existing Jinja page remains active until migrated later.
```

### AboutPage.vue

```text
title: About
legacyTemplate: frontend/templates/about.html
legacyScript: None / page behavior may be inline or backend-rendered
description: Vue route placeholder for the about page. Existing Jinja page remains active until migrated later.
```

---

## frontend/vue/src/pages/VueSmokePage.vue

Keep the smoke test page, but update it to fit the new layout.

It must still:

- render successfully
- have a button counter
- verify Vue reactivity
- verify Tailwind styles

Required implementation:

```vue
<script setup>
import { ref } from "vue";
import AppPageHeader from "../components/AppPageHeader.vue";

const count = ref(0);
</script>

<template>
  <AppPageHeader
    title="Vue Smoke Test"
    description="Confirms Vue 3, Vue Router, Pinia, Vite, Tailwind, and the shared layout are wired correctly."
  />

  <section class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <p class="text-sm font-medium text-emerald-700">Vue is mounted</p>

    <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
      Infrastructure check
    </h2>

    <p class="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
      This route is intentionally kept as a development-only smoke page during the migration.
    </p>

    <button
      type="button"
      class="mt-6 rounded-xl bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
      @click="count += 1"
    >
      Clicked {{ count }} times
    </button>
  </section>
</template>
```

---

## frontend/vue/src/pages/NotFoundPage.vue

Create:

```vue
<script setup>
import { useRoute } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";

const route = useRoute();
</script>

<template>
  <AppPageHeader
    title="Page not found"
    description="The requested Vue route does not exist."
  />

  <section class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <p class="text-sm text-slate-600">
      No Vue route matches:
      <code class="rounded bg-slate-100 px-2 py-1 font-mono text-slate-900">
        {{ route.fullPath }}
      </code>
    </p>

    <RouterLink
      to="/dashboard"
      class="mt-6 inline-flex rounded-xl bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
    >
      Go to Dashboard
    </RouterLink>
  </section>
</template>
```

---

## frontend/vue/src/router/index.js

Replace the smoke-only router with the full route skeleton.

Required implementation:

```js
import { createRouter, createWebHistory } from "vue-router";

import AboutPage from "../pages/AboutPage.vue";
import AnalyticsPage from "../pages/AnalyticsPage.vue";
import ApplicationsPage from "../pages/ApplicationsPage.vue";
import ApplyPage from "../pages/ApplyPage.vue";
import CompaniesPage from "../pages/CompaniesPage.vue";
import DashboardPage from "../pages/DashboardPage.vue";
import DraftDetailPage from "../pages/DraftDetailPage.vue";
import DraftsPage from "../pages/DraftsPage.vue";
import HelpPage from "../pages/HelpPage.vue";
import JobsPage from "../pages/JobsPage.vue";
import OfferCompassPage from "../pages/OfferCompassPage.vue";
import OnboardingPage from "../pages/OnboardingPage.vue";
import SettingsPage from "../pages/SettingsPage.vue";
import SetupRequiredPage from "../pages/SetupRequiredPage.vue";
import StoryBankPage from "../pages/StoryBankPage.vue";
import ThesisPage from "../pages/ThesisPage.vue";
import VerifiedFactsPage from "../pages/VerifiedFactsPage.vue";
import WorkspaceResetPage from "../pages/WorkspaceResetPage.vue";
import VueSmokePage from "../pages/VueSmokePage.vue";
import NotFoundPage from "../pages/NotFoundPage.vue";

const routes = [
  {
    path: "/",
    redirect: "/dashboard"
  },
  {
    path: "/vue-smoke",
    name: "vue-smoke",
    component: VueSmokePage
  },
  {
    path: "/dashboard",
    name: "dashboard",
    component: DashboardPage
  },
  {
    path: "/jobs",
    name: "jobs",
    component: JobsPage
  },
  {
    path: "/companies",
    name: "companies",
    component: CompaniesPage
  },
  {
    path: "/apply",
    name: "apply",
    component: ApplyPage
  },
  {
    path: "/applications",
    name: "applications",
    component: ApplicationsPage
  },
  {
    path: "/drafts",
    name: "drafts",
    component: DraftsPage
  },
  {
    path: "/drafts/:id",
    name: "draft-detail",
    component: DraftDetailPage
  },
  {
    path: "/onboarding",
    name: "onboarding",
    component: OnboardingPage
  },
  {
    path: "/settings",
    name: "settings",
    component: SettingsPage
  },
  {
    path: "/setup-required",
    name: "setup-required",
    component: SetupRequiredPage
  },
  {
    path: "/verified-facts",
    name: "verified-facts",
    component: VerifiedFactsPage
  },
  {
    path: "/story-bank",
    name: "story-bank",
    component: StoryBankPage
  },
  {
    path: "/offer-compass",
    name: "offer-compass",
    component: OfferCompassPage
  },
  {
    path: "/analytics",
    name: "analytics",
    component: AnalyticsPage
  },
  {
    path: "/thesis",
    name: "thesis",
    component: ThesisPage
  },
  {
    path: "/workspace-reset",
    name: "workspace-reset",
    component: WorkspaceResetPage
  },
  {
    path: "/help",
    name: "help",
    component: HelpPage
  },
  {
    path: "/about",
    name: "about",
    component: AboutPage
  },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: NotFoundPage
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;
```

---

## frontend/vue/src/App.vue

Keep it simple:

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

---

## Styling Requirements

Use Tailwind classes only.

Keep style minimal and consistent:

```text
white / slate background
dark slate sidebar
rounded cards
bordered panels
clean readable spacing
```

Do not add new CSS files except those already listed.

Do not introduce custom design systems.

Do not install icon libraries.

---

## Validation Commands

Run:

```bash
npm run build:vue
```

Run existing frontend build command if present:

```bash
npm run css:build
```

Run tests:

```bash
pytest
```

If `pytest` fails because of unrelated pre-existing failures, report the exact failures and confirm whether any failure is caused by this task.

---

## Manual Validation

Run:

```bash
npm run dev:vue
```

Open these routes:

```text
http://localhost:5173/
http://localhost:5173/vue-smoke
http://localhost:5173/dashboard
http://localhost:5173/jobs
http://localhost:5173/apply
http://localhost:5173/drafts/123
http://localhost:5173/settings
http://localhost:5173/verified-facts
http://localhost:5173/not-a-real-route
```

Expected:

- `/` redirects to `/dashboard`
- Sidebar appears
- Topbar appears
- Navigation links work
- Each page shows a placeholder card
- `/drafts/123` shows draft ID `123`
- unknown route shows NotFoundPage
- `/vue-smoke` button counter still works
- browser console has no errors
- no legacy Jinja page is changed
- no backend route is changed

---

## Acceptance Criteria

This task is complete only if:

1. Full Vue route skeleton exists.
2. Shared layout uses `AppSidebar` and `AppTopbar`.
3. Sidebar navigation contains all required groups and links.
4. All existing legacy pages have matching Vue placeholder pages.
5. `VueSmokePage` still works.
6. `DraftDetailPage` reads route param ID.
7. `NotFoundPage` works.
8. Pinia remains installed and configured from previous task.
9. `npm run build:vue` succeeds.
10. Existing Jinja templates are untouched.
11. Existing static JS files are untouched.
12. Backend business logic is untouched.
13. No page behavior is migrated yet.

---

## Forbidden Outcomes

Do not:

- convert real page logic
- delete Jinja templates
- delete static JS
- remove HTMX
- remove Alpine
- add backend APIs
- add FastAPI SPA catch-all route
- modify `/ui/*` routes
- move LLM calls
- touch CV generation logic
- touch verified-fact validation
- touch human approval workflow
- use Vuex
- replace Pinia
- add TypeScript
- add Nuxt
- add icon libraries
- add Docker
- change package manager

---

## Final Codex Response

Report:

1. files added
2. files modified
3. commands run
4. build result
5. test result
6. manual validation result
7. whether any failing tests are pre-existing or caused by this task
8. known issues

Do not continue to page migration.
