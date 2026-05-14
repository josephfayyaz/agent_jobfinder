<script setup>
defineProps({
  message: {
    type: String,
    default: "",
  },
  tone: {
    type: String,
    default: "neutral",
  },
});
</script>

<template>
  <p
    v-if="message"
    :class="[
      'text-sm font-medium',
      tone === 'error'
        ? 'text-rose-700'
        : tone === 'success'
          ? 'text-emerald-700'
          : 'text-slate-600'
    ]"
  >
    {{ message }}
  </p>
</template>
