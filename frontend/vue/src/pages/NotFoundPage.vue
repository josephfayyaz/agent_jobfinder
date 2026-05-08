<script setup>
import { useRoute } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";

const route = useRoute();
</script>

<template>
  <AppPageHeader
    title="Page not found"
    description="The requested Vue route does not exist."
  />

  <section class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <p class="text-sm text-slate-600">
      No Vue route matches:
      <code class="rounded bg-slate-100 px-2 py-1 font-mono text-slate-900">
        {{ route.fullPath }}
      </code>
    </p>

    <RouterLink
      to="/dashboard"
      class="mt-6 inline-flex rounded-xl bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
    >
      Go to Dashboard
    </RouterLink>
  </section>
</template>
