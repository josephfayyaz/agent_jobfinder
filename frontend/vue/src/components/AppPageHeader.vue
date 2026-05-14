<script setup>
defineProps({
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ""
  }
});
</script>

<template>
  <div class="mb-6">
    <h1 class="mt-1 text-3xl font-semibold tracking-tight text-slate-950">
      {{ title }}
    </h1>
<!--    <p v-if="description" class="mt-3 max-w-3xl text-sm leading-6 text-slate-600">-->
<!--      {{ description }}-->
<!--    </p>-->
  </div>
</template>
