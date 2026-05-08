<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";
import { vueApiFetch } from "../api/client";

const loading = ref(true);
const error = ref("");
const statusPayload = ref(null);
const previewPayload = ref(null);

onMounted(async () => {
  try {
    const [status, preview] = await Promise.all([
      vueApiFetch("/workspace/status"),
      vueApiFetch("/workspace/reset-preview", {
        method: "POST",
        body: JSON.stringify({
          include_generated_files: false,
          include_cached_results: false,
        }),
      }),
    ]);
    statusPayload.value = status;
    previewPayload.value = preview;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});

const statusData = computed(() => statusPayload.value?.data ?? {});
const statusMsg = computed(() => statusPayload.value?.message ?? "");
const isStatusPlaceholder = computed(() => (statusPayload.value?.status ?? "") === "placeholder");

const previewData = computed(() => previewPayload.value?.data ?? {});
const previewMsg = computed(() => previewPayload.value?.message ?? "");
const isPreviewPlaceholder = computed(() => (previewPayload.value?.status ?? "") === "placeholder");

// Workspace status fields — all booleans/counts, no paths
const localFirst = computed(() =>
  typeof statusData.value.local_first === "boolean" ? statusData.value.local_first : null
);
const hasBackupableDb = computed(() =>
  typeof statusData.value.has_backupable_db === "boolean" ? statusData.value.has_backupable_db : null
);
const backupCount = computed(() =>
  typeof statusData.value.backup_count === "number" ? statusData.value.backup_count : null
);
const legacyRuntimePresent = computed(() =>
  typeof statusData.value.legacy_runtime_present === "boolean" ? statusData.value.legacy_runtime_present : null
);

// Preview fields — safe read-only indicators only
const destructiveActionTaken = computed(() =>
  // backend uses destructive_action_taken; spec example uses destructive_action_performed — handle both
  typeof previewData.value.destructive_action_taken === "boolean"
    ? previewData.value.destructive_action_taken
    : typeof previewData.value.destructive_action_performed === "boolean"
    ? previewData.value.destructive_action_performed
    : false
);
const wouldAffectGenerated = computed(() =>
  typeof previewData.value.would_affect_generated_files === "boolean"
    ? previewData.value.would_affect_generated_files
    : null
);
const wouldAffectCached = computed(() =>
  typeof previewData.value.would_affect_cached_results === "boolean"
    ? previewData.value.would_affect_cached_results
    : null
);
const previewBackupCount = computed(() =>
  typeof previewData.value.backup_count === "number" ? previewData.value.backup_count : null
);
const previewHasBackupableDb = computed(() =>
  typeof previewData.value.has_backupable_db === "boolean" ? previewData.value.has_backupable_db : null
);
</script>

<template>
  <AppPageHeader
    title="Workspace Reset"
    description="A read-only status and preview view. No reset, delete, or backup actions are available from this page."
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <div class="space-y-6 lg:col-span-2">

      <!-- Workspace status -->
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Workspace status</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
          Local workspace
        </h2>

        <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Loading workspace status...
        </div>

        <div v-else-if="error" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          {{ error }}
        </div>

        <div v-else class="mt-4 space-y-4">
          <p v-if="statusMsg" class="text-sm leading-6 text-slate-600">{{ statusMsg }}</p>

          <div
            v-if="isStatusPlaceholder"
            class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
          >
            Workspace status is returning placeholder data. No local paths or secrets are shown.
          </div>

          <dl class="grid gap-4 text-sm md:grid-cols-2">
            <div v-if="localFirst !== null" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <dt class="text-slate-500">Storage model</dt>
              <dd class="mt-1 font-semibold text-slate-950">
                {{ localFirst ? "Local-first (no cloud sync)" : "Standard" }}
              </dd>
            </div>

            <div v-if="hasBackupableDb !== null" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <dt class="text-slate-500">Database backup available</dt>
              <dd class="mt-1">
                <span
                  :class="[
                    'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold',
                    hasBackupableDb
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                      : 'border-slate-200 bg-slate-50 text-slate-600'
                  ]"
                >
                  {{ hasBackupableDb ? "Yes" : "No" }}
                </span>
              </dd>
            </div>

            <div v-if="backupCount !== null" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <dt class="text-slate-500">Existing backups</dt>
              <dd class="mt-1 text-xl font-bold text-slate-950">{{ backupCount }}</dd>
            </div>

            <div v-if="legacyRuntimePresent !== null" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <dt class="text-slate-500">Legacy runtime</dt>
              <dd class="mt-1">
                <span
                  :class="[
                    'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold',
                    legacyRuntimePresent
                      ? 'border-amber-200 bg-amber-50 text-amber-800'
                      : 'border-slate-200 bg-slate-50 text-slate-600'
                  ]"
                >
                  {{ legacyRuntimePresent ? "Present" : "Not present" }}
                </span>
              </dd>
            </div>
          </dl>

          <p
            v-if="localFirst === null && hasBackupableDb === null && backupCount === null"
            class="text-sm text-slate-600"
          >
            Workspace status not available.
          </p>
        </div>
      </article>

      <!-- Reset preview -->
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Reset preview</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">What a reset would affect</h2>
        <p class="mt-1 text-sm text-slate-500">Preview computed with no files selected. No action was taken.</p>

        <div v-if="loading" class="mt-4 text-sm text-slate-600">Loading preview...</div>

        <div v-else class="mt-4 space-y-4">
          <p v-if="previewMsg" class="text-sm leading-6 text-slate-600">{{ previewMsg }}</p>

          <div
            v-if="isPreviewPlaceholder"
            class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
          >
            Reset preview is returning placeholder data.
          </div>

          <!-- Destructive action confirmation -->
          <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
            <p class="font-semibold">No destructive action was performed</p>
            <p class="mt-1 opacity-75">
              This is a read-only preview. The backend confirmed:
              <code class="rounded bg-emerald-100 px-1 font-mono text-xs">destructive_action_taken = {{ destructiveActionTaken }}</code>
            </p>
          </div>

          <dl class="grid gap-3 text-sm md:grid-cols-2">
            <div v-if="wouldAffectGenerated !== null" class="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
              <dt class="text-slate-600">Would affect generated files</dt>
              <dd>
                <span class="inline-flex items-center rounded border border-slate-200 bg-white px-1.5 py-0.5 text-xs font-medium text-slate-700">
                  {{ wouldAffectGenerated ? "Yes" : "No" }}
                </span>
              </dd>
            </div>

            <div v-if="wouldAffectCached !== null" class="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
              <dt class="text-slate-600">Would affect cached results</dt>
              <dd>
                <span class="inline-flex items-center rounded border border-slate-200 bg-white px-1.5 py-0.5 text-xs font-medium text-slate-700">
                  {{ wouldAffectCached ? "Yes" : "No" }}
                </span>
              </dd>
            </div>

            <div v-if="previewBackupCount !== null" class="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
              <dt class="text-slate-600">Available backups</dt>
              <dd class="font-semibold text-slate-950">{{ previewBackupCount }}</dd>
            </div>

            <div v-if="previewHasBackupableDb !== null" class="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
              <dt class="text-slate-600">DB backupable</dt>
              <dd>
                <span
                  :class="[
                    'inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium',
                    previewHasBackupableDb
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                      : 'border-slate-200 bg-white text-slate-500'
                  ]"
                >
                  {{ previewHasBackupableDb ? "Yes" : "No" }}
                </span>
              </dd>
            </div>
          </dl>
        </div>
      </article>

      <!-- Future actions (all disabled) -->
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Future actions</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">Workspace controls</h2>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          These controls will be enabled in a future migration phase. They are shown here as disabled placeholders and do not call any endpoints.
        </p>

        <div class="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            disabled
            class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-500 opacity-50 cursor-not-allowed"
          >
            Create backup
          </button>
          <button
            type="button"
            disabled
            class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-500 opacity-50 cursor-not-allowed"
          >
            Reset workspace
          </button>
          <button
            type="button"
            disabled
            class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-500 opacity-50 cursor-not-allowed"
          >
            Delete workspace
          </button>
        </div>
      </article>

    </div>

    <!-- Sidebar -->
    <aside class="space-y-4">

      <!-- Read-only safety notice -->
      <div class="rounded-2xl border border-amber-200 bg-amber-50 p-6 shadow-sm">
        <p class="text-sm font-medium text-amber-900">Read-only safety</p>
        <p class="mt-2 text-sm leading-6 text-amber-800">
          No reset, delete, or backup actions are available from this Vue page. This page shows a safe read-only status and a non-destructive preview only.
        </p>
        <p class="mt-3 text-sm leading-6 text-amber-800">
          To manage your workspace, use the legacy interface at
          <code class="rounded bg-amber-100 px-1 font-mono text-xs">/ui/workspace-reset</code>
          while Vue migration is in progress.
        </p>
      </div>

      <!-- Navigation -->
      <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <p class="text-sm font-medium text-slate-500">Next actions</p>
          <p class="mt-2 text-sm leading-6 text-slate-600">
            Review your settings or return to the dashboard. Workspace management controls require the legacy interface.
          </p>
        </div>

        <dl class="mt-4 space-y-3 text-sm">
          <div class="flex items-start justify-between gap-4">
            <dt class="text-slate-500">Loading</dt>
            <dd class="font-medium text-slate-950">{{ loading ? "Yes" : "No" }}</dd>
          </div>
          <div class="flex items-start justify-between gap-4">
            <dt class="text-slate-500">Error</dt>
            <dd class="font-medium text-slate-950">{{ error ? "Present" : "None" }}</dd>
          </div>
          <div class="flex items-start justify-between gap-4">
            <dt class="text-slate-500">Destructive action taken</dt>
            <dd>
              <span class="inline-flex items-center rounded border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-xs font-semibold text-emerald-800">
                {{ destructiveActionTaken ? "Yes" : "No" }}
              </span>
            </dd>
          </div>
          <div v-if="backupCount !== null" class="flex items-start justify-between gap-4">
            <dt class="text-slate-500">Backups</dt>
            <dd class="font-medium text-slate-950">{{ backupCount }}</dd>
          </div>
        </dl>

        <div class="mt-4 space-y-3">
          <RouterLink
            to="/dashboard"
            class="block rounded-xl bg-slate-950 px-4 py-2 text-center text-sm font-medium text-white hover:bg-slate-800"
          >
            Go to Dashboard
          </RouterLink>
          <RouterLink
            to="/settings"
            class="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-center text-sm font-medium text-slate-900 hover:bg-slate-100"
          >
            Settings
          </RouterLink>
          <RouterLink
            to="/help"
            class="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-center text-sm font-medium text-slate-900 hover:bg-slate-100"
          >
            Help
          </RouterLink>
          <RouterLink
            to="/about"
            class="block rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-center text-sm font-medium text-emerald-900 hover:bg-emerald-100"
          >
            About
          </RouterLink>
        </div>
      </div>

    </aside>
  </section>
</template>
