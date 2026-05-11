<script setup>
defineProps({
  trackStatus: { type: String, default: "" },
});
</script>

<template>
  <section class="rounded-lg border border-emerald-200 bg-emerald-50 p-6 shadow-sm">
    <p class="text-xs font-semibold uppercase tracking-wide text-emerald-700">Ready</p>
    <h2 class="mt-2 text-2xl font-semibold text-emerald-800">Your workspace is ready</h2>
    <p class="mt-2 text-sm leading-6 text-slate-700">
      You can now review jobs, apply interactively, generate drafts, and save verified profile
      memory.
    </p>
    <p
      v-if="trackStatus"
      class="mt-3 text-sm font-semibold text-indigo-700"
      :class="trackStatus === 'Building role tracks...' ? 'animate-pulse' : ''"
    >
      {{ trackStatus }}
    </p>
    <div class="mt-5 flex flex-wrap gap-3">
      <a
        class="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800"
        href="/ui/jobs"
      >
        Find jobs now
      </a>
      <a
        class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
        href="/ui"
      >
        Continue to dashboard
      </a>
    </div>
  </section>
</template>
