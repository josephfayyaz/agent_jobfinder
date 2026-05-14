<script setup>
import SettingsStatusMessage from "./SettingsStatusMessage.vue";

const props = defineProps({
  maintenance: {
    type: Object,
    required: true,
  },
  maintenanceStatus: {
    type: Object,
    required: true,
  },
  resetStatus: {
    type: Object,
    required: true,
  },
  deleteStatus: {
    type: Object,
    required: true,
  },
  busy: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update:field", "reload-settings", "copy-share", "run-danger-action"]);

function update(field, event) {
  emit("update:field", field, event.target.type === "checkbox" ? event.target.checked : event.target.value);
}
</script>

<template>
  <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
    <div>
      <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Workspace</p>
      <h2 class="mt-1 text-xl font-semibold text-slate-950">Maintenance and ownership</h2>
    </div>

    <div class="mt-5 grid gap-4 lg:grid-cols-2">
      <div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <h3 class="text-sm font-semibold text-slate-950">Share Job Agent</h3>
        <p class="mt-2 break-all rounded-md border border-slate-200 bg-white px-3 py-2 font-mono text-xs text-slate-600">
          {{ props.maintenance.shareUrl || "No share link configured" }}
        </p>
        <div class="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            class="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-sky-800"
            @click="emit('copy-share')"
          >
            Copy Share Link
          </button>
          <a
            v-if="props.maintenance.shareUrl"
            :href="props.maintenance.shareUrl"
            target="_blank"
            rel="noreferrer"
            class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
          >
            Open GitHub
          </a>
        </div>
      </div>

      <div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <h3 class="text-sm font-semibold text-slate-950">Operational actions</h3>
        <p class="mt-2 text-sm text-slate-600">Saved backups: {{ props.maintenance.backupCount }}</p>
        <div class="mt-4 flex flex-wrap gap-3">
          <a
            href="/workspace/download"
            class="rounded-md border border-emerald-200 bg-white px-4 py-2 text-sm font-semibold text-emerald-700 shadow-sm hover:bg-emerald-50"
          >
            Download My Data
          </a>
          <button
            type="button"
            class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
            :disabled="busy"
            @click="emit('reload-settings')"
          >
            Reload Settings
          </button>
        </div>
      </div>
    </div>

    <SettingsStatusMessage
      class="mt-4 block"
      :message="maintenanceStatus.message"
      :tone="maintenanceStatus.tone"
    />

    <div class="mt-6 rounded-lg border border-rose-200 bg-rose-50 p-4">
      <h3 class="text-sm font-semibold text-rose-900">Danger zone</h3>
      <div class="mt-4 grid gap-4 lg:grid-cols-2">
        <div class="rounded-lg border border-amber-200 bg-white p-4">
          <p class="text-sm font-semibold text-slate-950">Start Fresh</p>
          <label class="mt-3 block">
            <span class="text-sm font-medium text-slate-700">Type {{ props.maintenance.resetPhrase }}</span>
            <input
              :value="props.maintenance.resetInput"
              type="text"
              class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
              @input="update('resetInput', $event)"
            />
          </label>
          <label class="mt-3 flex items-center gap-3 text-sm text-slate-700">
            <input
              :checked="props.maintenance.openBackups"
              type="checkbox"
              class="h-4 w-4 rounded border-slate-300 text-sky-700 focus:ring-sky-500"
              @change="update('openBackups', $event)"
            />
            Open backup folder after reset
          </label>
          <div class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <SettingsStatusMessage :message="resetStatus.message" :tone="resetStatus.tone" />
            <button
              type="button"
              class="rounded-md border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-800 shadow-sm hover:bg-amber-100 disabled:cursor-not-allowed disabled:text-amber-300"
              :disabled="busy"
              @click="emit('run-danger-action', 'reset')"
            >
              Start Fresh
            </button>
          </div>
        </div>

        <div class="rounded-lg border border-rose-200 bg-white p-4">
          <p class="text-sm font-semibold text-slate-950">Erase Local Data</p>
          <label class="mt-3 block">
            <span class="text-sm font-medium text-slate-700">Type {{ props.maintenance.deletePhrase }}</span>
            <input
              :value="props.maintenance.deleteInput"
              type="text"
              class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
              @input="update('deleteInput', $event)"
            />
          </label>
          <div class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <SettingsStatusMessage :message="deleteStatus.message" :tone="deleteStatus.tone" />
            <button
              type="button"
              class="rounded-md border border-rose-300 bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-800 shadow-sm hover:bg-rose-100 disabled:cursor-not-allowed disabled:text-rose-300"
              :disabled="busy"
              @click="emit('run-danger-action', 'delete')"
            >
              Erase Local Data
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
