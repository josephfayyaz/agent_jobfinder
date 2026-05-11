<script setup>
import { RouterLink } from "vue-router";
import AppPageHeader from "../AppPageHeader.vue";

defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    default: "",
  },
});
</script>

<template>
  <div class="space-y-6">
    <AppPageHeader :title="title" :description="description" />

    <nav class="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
      <RouterLink
        to="/settings/ai-provider"
        class="rounded-md px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-white hover:text-slate-950"
        active-class="bg-white text-slate-950 shadow-sm ring-1 ring-slate-200"
      >
        AI Provider
      </RouterLink>
      <RouterLink
        to="/settings/workspace"
        class="rounded-md px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-white hover:text-slate-950"
        active-class="bg-white text-slate-950 shadow-sm ring-1 ring-slate-200"
      >
        Workspace Settings
      </RouterLink>
    </nav>

    <slot />
  </div>
</template>
