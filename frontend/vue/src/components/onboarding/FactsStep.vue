<script setup>
import StatusMessage from "./StatusMessage.vue";

defineProps({
  facts: { type: Object, required: true },
});

const emit = defineEmits(["back"]);
</script>

<template>
  <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
    <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Facts</p>
        <h2 class="mt-1 text-2xl font-semibold text-slate-950">Build your fact sheet</h2>
        <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Upload one or more CV files and add optional notes for recent updates not included in those files.
        </p>
      </div>
    </div>

    <div class="mt-6 space-y-5">
      <label class="block">
        <span class="text-sm font-medium text-slate-700">Source files</span>
        <input
          class="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm file:mr-4 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-slate-700 hover:file:bg-slate-200 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          type="file"
          multiple
          accept=".pdf,.txt,.md,.rst,application/pdf,text/plain,text/markdown"
          :disabled="facts.factsBusy.value"
          @change="facts.handleSourceFiles"
        />
      </label>

      <div
        v-if="facts.selectedFileNames.value.length"
        class="rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700"
      >
        <p class="font-semibold text-slate-900">Selected files</p>
        <ul class="mt-2 space-y-1">
          <li v-for="name in facts.selectedFileNames.value" :key="name">{{ name }}</li>
        </ul>
      </div>

      <label class="block">
        <span class="text-sm font-medium text-slate-700">Optional manual notes</span>
        <textarea
          v-model="facts.profileNotes.value"
          class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          rows="7"
          placeholder="Recent roles, tools, projects, education, languages, achievements..."
          :disabled="facts.factsBusy.value"
        ></textarea>
      </label>

      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <StatusMessage
          :message="facts.factsStatus.value"
          :is-error="facts.factsStatusError.value"
        />
        <div class="flex gap-3">
          <button
            type="button"
            class="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="facts.factsBusy.value"
            @click="emit('back')"
          >
            Back
          </button>
          <button
            type="button"
            class="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            :disabled="facts.factsBusy.value"
            @click="facts.runFactsIntake"
          >
            {{ facts.factsBusy.value ? "Analysing..." : "Analyse my profile" }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
