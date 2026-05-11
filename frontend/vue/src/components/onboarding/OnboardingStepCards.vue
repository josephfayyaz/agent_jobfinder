<script setup>
defineProps({
  steps: { type: Array, required: true },
});

const emit = defineEmits(["select"]);
</script>

<template>
  <nav
    aria-label="Onboarding progress"
    class="rounded-xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4"
  >
    <ol class="grid gap-3 md:grid-cols-5">
      <li
        v-for="step in steps"
        :key="step.key"
        class="min-w-0"
      >
        <button
          type="button"
          class="group flex h-full w-full gap-3 rounded-lg border p-3 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 sm:p-4"
          :class="[
            step.active ? 'border-sky-500 bg-sky-50 ring-2 ring-sky-100' : '',
            step.completed && !step.active ? 'border-emerald-200 bg-emerald-50/70 hover:border-emerald-300' : '',
            step.disabled ? 'cursor-not-allowed border-slate-200 bg-slate-50 opacity-70' : '',
            !step.active && !step.completed && !step.disabled ? 'border-slate-200 bg-white hover:border-sky-300 hover:bg-sky-50/50' : '',
          ]"
          :aria-current="step.active ? 'step' : undefined"
          :aria-disabled="step.disabled ? 'true' : 'false'"
          :aria-label="`Step ${step.index}: ${step.title}. ${step.statusText}.`"
          :disabled="step.disabled"
          @click="emit('select', step.key)"
        >
          <span
            class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-sm font-semibold"
            :class="[
              step.active ? 'border-sky-600 bg-sky-700 text-white' : '',
              step.completed && !step.active ? 'border-emerald-500 bg-emerald-600 text-white' : '',
              step.disabled ? 'border-slate-200 bg-white text-slate-400' : '',
              !step.active && !step.completed && !step.disabled ? 'border-slate-300 bg-white text-slate-700 group-hover:border-sky-300' : '',
            ]"
            aria-hidden="true"
          >
            {{ step.index }}
          </span>

          <span class="min-w-0">
            <span class="block text-xs font-semibold uppercase tracking-wide text-slate-500">
              Step {{ step.index }}
            </span>
            <span class="mt-1 block text-sm font-semibold text-slate-950 sm:text-base">
              {{ step.title }}
            </span>
            <span
              class="mt-2 inline-flex rounded-full px-2 py-0.5 text-xs font-semibold"
              :class="[
                step.active ? 'bg-sky-100 text-sky-800' : '',
                step.completed && !step.active ? 'bg-emerald-100 text-emerald-800' : '',
                step.disabled ? 'bg-slate-100 text-slate-500' : '',
                !step.active && !step.completed && !step.disabled ? 'bg-slate-100 text-slate-700' : '',
              ]"
            >
              {{ step.statusText }}
            </span>
          </span>
        </button>
      </li>
    </ol>
  </nav>
</template>
