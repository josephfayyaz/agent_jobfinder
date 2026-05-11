<script setup>
import { navigationGroups } from "../constants/navigation";
</script>

<template>
  <aside class="hidden min-h-screen w-72 shrink-0 border-r border-slate-200 bg-slate-950 text-white lg:block">
    <div class="px-6 py-6">
      <RouterLink
        to="/"
        data-testid="brand-home-link"
        class="block text-lg font-semibold text-white hover:text-slate-200"
      >
        Agent Jobfinder
      </RouterLink>
    </div>

    <nav data-testid="sidebar-nav" class="space-y-6 px-4 pb-8">
      <section v-for="group in navigationGroups" :key="group.label">
        <h3 class="px-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          {{ group.label }}
        </h3>

        <div class="mt-2 space-y-1">
          <RouterLink
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            class="block rounded-xl px-3 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white"
            active-class="bg-slate-800 text-white"
          >
            {{ item.label }}
          </RouterLink>
        </div>
      </section>
    </nav>
  </aside>
</template>
