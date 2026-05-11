<script setup>
import SettingsStatusMessage from "./SettingsStatusMessage.vue";

const props = defineProps({
  cv: {
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

const emit = defineEmits(["update:field", "save"]);

function update(field, event) {
  emit("update:field", field, event.target.value);
}
</script>

<template>
  <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
    <div>
      <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">CV settings</p>
      <h2 class="mt-1 text-xl font-semibold text-slate-950">Review thresholds</h2>
    </div>

    <div class="mt-5 grid gap-4 md:grid-cols-3">
      <label class="block">
        <span class="text-sm font-medium text-slate-700">CV pass score</span>
        <input
          :value="props.cv.cvPassScore"
          type="number"
          min="60"
          max="100"
          class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          @input="update('cvPassScore', $event)"
        />
      </label>
      <label class="block">
        <span class="text-sm font-medium text-slate-700">CV revise score</span>
        <input
          :value="props.cv.cvReviseScore"
          type="number"
          min="40"
          max="90"
          class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          @input="update('cvReviseScore', $event)"
        />
      </label>
      <label class="block">
        <span class="text-sm font-medium text-slate-700">Bullet word limit</span>
        <input
          :value="props.cv.bulletClarifyWordLimit"
          type="number"
          min="10"
          max="50"
          class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          @input="update('bulletClarifyWordLimit', $event)"
        />
      </label>
    </div>

    <div class="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <SettingsStatusMessage :message="status.message" :tone="status.tone" />
      <button
        type="button"
        class="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        :disabled="saving"
        @click="emit('save')"
      >
        {{ saving ? "Saving..." : "Save CV Settings" }}
      </button>
    </div>
  </section>
</template>
