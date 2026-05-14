<script setup>
import SettingsStatusMessage from "./SettingsStatusMessage.vue";

defineProps({
  status: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <div class="min-h-5">
    <SettingsStatusMessage :message="status.message" :tone="status.tone" />
  </div>
</template>
