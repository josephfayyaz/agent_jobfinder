<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";

import AppLayout from "./layouts/AppLayout.vue";
import BlankLayout from "./layouts/BlankLayout.vue";

const route = useRoute();
const activeLayout = computed(() => (route.meta.layout === "blank" ? BlankLayout : AppLayout));
</script>

<template>
  <component :is="activeLayout">
    <router-view />
  </component>
</template>
