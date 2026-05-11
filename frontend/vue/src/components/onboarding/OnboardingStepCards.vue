<script setup>
defineProps({
  steps: { type: Array, required: true },
});

const emit = defineEmits(["select"]);
</script>

<template>
  <section class="grid gap-3 md:grid-cols-5">
    <button
      v-for="step in steps"
      :key="step.key"
      type="button"
      class="rounded-lg border bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-sky-300 hover:shadow-md"
      :class="[
        step.active ? 'border-sky-500 ring-2 ring-sky-100' : 'border-slate-200',
        step.completed ? 'bg-emerald-50/60' : '',
      ]"
      @click="emit('select', step.key)"
    >
      <div class="flex items-center justify-between gap-2">
        <span class="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Step {{ step.index }}
        </span>
        <span
          class="rounded-full px-2 py-0.5 text-xs font-semibold"
          :class="step.completed ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'"
        >
          {{ step.statusText }}
        </span>
      </div>
      <h2 class="mt-3 text-xl font-semibold text-slate-950">{{ step.label }}</h2>
      <p class="mt-1 text-sm text-slate-600">{{ step.title }}</p>
    </button>
  </section>
</template>
