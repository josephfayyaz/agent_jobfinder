<script setup>
import SettingsStatusMessage from "./SettingsStatusMessage.vue";

const props = defineProps({
  gmail: {
    type: Object,
    required: true,
  },
  status: {
    type: Object,
    required: true,
  },
  saving: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update:field", "save", "connect-gmail", "disconnect-gmail"]);

function update(field, event) {
  emit("update:field", field, event.target.type === "checkbox" ? event.target.checked : event.target.value);
}
</script>

<template>
  <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Gmail integration</p>
        <h2 class="mt-1 text-xl font-semibold text-slate-950">LinkedIn alert intake</h2>
      </div>
      <span
        :class="[
          'inline-flex rounded-md px-2 py-1 text-xs font-semibold',
          props.gmail.connected ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'
        ]"
      >
        {{ props.gmail.connected ? "OAuth connected" : "Not connected" }}
      </span>
    </div>

    <div class="mt-5 grid gap-4 md:grid-cols-2">
      <label class="block">
        <span class="text-sm font-medium text-slate-700">Google Client ID</span>
        <input
          :value="props.gmail.clientId"
          type="text"
          autocomplete="off"
          placeholder="Leave blank to keep the saved value"
          class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          @input="update('clientId', $event)"
        />
      </label>
      <label class="block">
        <span class="text-sm font-medium text-slate-700">Google Client Secret</span>
        <input
          :value="props.gmail.clientSecret"
          type="password"
          autocomplete="off"
          placeholder="Leave blank to keep the saved value"
          class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          @input="update('clientSecret', $event)"
        />
      </label>
      <label class="block">
        <span class="text-sm font-medium text-slate-700">Gmail label filter</span>
        <input
          :value="props.gmail.labelFilter"
          type="text"
          class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          @input="update('labelFilter', $event)"
        />
      </label>
      <label class="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
        <span>
          <span class="block text-sm font-medium text-slate-700">Auto-sync Gmail</span>
          <span class="mt-1 block text-xs text-slate-500">Automatically import matching job alerts.</span>
        </span>
        <input
          :checked="props.gmail.autoSync"
          type="checkbox"
          class="h-5 w-5 rounded border-slate-300 text-sky-700 focus:ring-sky-500"
          @change="update('autoSync', $event)"
        />
      </label>
    </div>

    <div class="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <SettingsStatusMessage :message="status.message" :tone="status.tone" />
      <div class="flex flex-wrap gap-3">
        <button
          type="button"
          class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
          :disabled="saving"
          @click="emit('save')"
        >
          Save Gmail Settings
        </button>
        <button
          type="button"
          class="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          :disabled="saving"
          @click="emit('connect-gmail')"
        >
          Connect Gmail
        </button>
        <button
          type="button"
          class="rounded-md border border-rose-200 bg-white px-4 py-2 text-sm font-semibold text-rose-700 shadow-sm hover:bg-rose-50 disabled:cursor-not-allowed disabled:text-rose-300"
          :disabled="saving"
          @click="emit('disconnect-gmail')"
        >
          Disconnect
        </button>
      </div>
    </div>
  </section>
</template>
