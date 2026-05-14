<script setup>
import AppSidebar from "../components/AppSidebar.vue";
</script>

<template>
  <div class="min-h-screen bg-slate-50 text-slate-950">
    <div class="flex min-h-screen">
      <AppSidebar />
      <div class="flex min-w-0 flex-1 flex-col">
        <main class="flex-1 px-6 py-8">
          <div class="mx-auto max-w-7xl">
            <slot />
          </div>
        </main>
      </div>
    </div>
  </div>
</template>
