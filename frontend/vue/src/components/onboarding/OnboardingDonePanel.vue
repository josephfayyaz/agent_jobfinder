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
    <p class="mt-4 text-sm font-semibold text-emerald-800">
      Redirecting to dashboard...
    </p>
  </section>
</template>
