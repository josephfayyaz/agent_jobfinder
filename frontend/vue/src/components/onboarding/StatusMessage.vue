<script setup>
defineProps({
  message: { type: String, default: "" },
  isError: { type: Boolean, default: false },
  successClass: { type: String, default: "text-slate-600" },
});
</script>

<template>
  <p class="min-h-5 text-sm" :class="isError ? 'text-red-700' : successClass">
    {{ message }}
  </p>
</template>
