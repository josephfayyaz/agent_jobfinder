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
