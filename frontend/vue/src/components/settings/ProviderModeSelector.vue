<script setup>
defineProps({
  modelValue: {
    type: String,
    required: true,
  },
  providers: {
    type: Array,
    required: true,
  },
});

defineEmits(["update:modelValue"]);
</script>

<template>
  <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
    <div>
      <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Active provider</p>
      <h2 class="mt-1 text-xl font-semibold text-slate-950">Choose one AI runtime</h2>
    </div>

    <div class="mt-5 grid gap-3 md:grid-cols-5">
      <button
        v-for="provider in providers"
        :key="provider.value"
        type="button"
        class="min-h-28 rounded-lg border p-4 text-left transition focus:outline-none focus:ring-2 focus:ring-sky-100"
        :class="modelValue === provider.value ? 'border-sky-500 bg-sky-50' : 'border-slate-200 bg-white hover:border-sky-300 hover:bg-slate-50'"
        @click="$emit('update:modelValue', provider.value)"
      >
        <span class="text-xs font-semibold uppercase tracking-wide text-slate-500">{{ provider.eyebrow }}</span>
        <span class="mt-2 block text-sm font-semibold text-slate-950">{{ provider.label }}</span>
        <span class="mt-1 block text-sm leading-5 text-slate-600">{{ provider.description }}</span>
      </button>
    </div>
  </section>
</template>
