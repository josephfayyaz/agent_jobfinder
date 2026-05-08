<script setup>
import { RouterLink } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";

const steps = [
  {
    number: 1,
    title: "Paste JD",
    description:
      "Future step for pasting a job description. Disabled until safe Vue apply migration is implemented.",
    status: "Disabled",
  },
  {
    number: 2,
    title: "Score",
    description:
      "Future step for matching the job against verified profile facts. Disabled; no scoring endpoint is called.",
    status: "Disabled",
  },
  {
    number: 3,
    title: "Questions",
    description:
      "Future step for clarifying missing information. Disabled; no question generation endpoint is called.",
    status: "Disabled",
  },
  {
    number: 4,
    title: "Draft",
    description:
      "Future step for creating a reviewable CV draft. Disabled; no CV generation endpoint is called.",
    status: "Disabled",
  },
];
</script>

<template>
  <AppPageHeader
    title="Apply"
    description="A read-only shell of the apply flow. No scoring, questions, or draft generation runs from this page."
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <div class="space-y-6 lg:col-span-2">

      <!-- Flow overview -->
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Apply flow preview</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
          How the apply flow works
        </h2>
        <p class="mt-3 text-sm leading-6 text-slate-600">
          The apply flow takes a job description and produces a tailored CV draft for your review. All four steps below are disabled in this Vue shell. Use the legacy interface at
          <code class="rounded bg-slate-100 px-1 font-mono text-xs">/ui/apply</code>
          to run the full flow while Vue migration is in progress.
        </p>

        <!-- Step flow indicator -->
        <div class="mt-6 flex flex-wrap items-center gap-2 text-sm">
          <span
            v-for="(step, index) in steps"
            :key="step.number"
            class="flex items-center gap-2"
          >
            <span class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 font-medium text-slate-400 opacity-60">
              <span class="flex h-5 w-5 items-center justify-center rounded-full border border-slate-300 bg-white text-xs font-semibold text-slate-400">
                {{ step.number }}
              </span>
              {{ step.title }}
            </span>
            <span v-if="index < steps.length - 1" class="text-slate-300">→</span>
          </span>
        </div>
      </article>

      <!-- Step 1: Paste JD -->
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm opacity-60">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-sm font-medium text-slate-500">Step 1</p>
            <h2 class="mt-1 text-xl font-semibold tracking-tight text-slate-950">Paste JD</h2>
          </div>
          <span class="inline-flex items-center rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-500 cursor-not-allowed">
            Disabled
          </span>
        </div>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          {{ steps[0].description }}
        </p>
        <div class="mt-4">
          <textarea
            disabled
            rows="5"
            placeholder="Paste job description here… (disabled)"
            class="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-400 placeholder-slate-300 cursor-not-allowed"
          />
          <div class="mt-3 flex gap-3">
            <button
              type="button"
              disabled
              class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-400 opacity-50 cursor-not-allowed"
            >
              Score this job →
            </button>
          </div>
        </div>
      </article>

      <!-- Steps 2–4 -->
      <article
        v-for="step in steps.slice(1)"
        :key="step.number"
        class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm opacity-60"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-sm font-medium text-slate-500">Step {{ step.number }}</p>
            <h2 class="mt-1 text-xl font-semibold tracking-tight text-slate-950">{{ step.title }}</h2>
          </div>
          <span class="inline-flex items-center rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-500 cursor-not-allowed">
            Disabled
          </span>
        </div>
        <p class="mt-2 text-sm leading-6 text-slate-600">{{ step.description }}</p>
        <div class="mt-4">
          <button
            type="button"
            disabled
            class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-400 opacity-50 cursor-not-allowed"
          >
            <span v-if="step.number === 2">Run score →</span>
            <span v-else-if="step.number === 3">Generate questions →</span>
            <span v-else-if="step.number === 4">Generate draft →</span>
          </button>
        </div>
      </article>

    </div>

    <!-- Sidebar -->
    <aside class="space-y-4">

      <!-- Read-only safety notice -->
      <div class="rounded-2xl border border-amber-200 bg-amber-50 p-6 shadow-sm">
        <p class="text-sm font-medium text-amber-900">Read-only safety</p>
        <p class="mt-2 text-sm leading-6 text-amber-800">
          This Vue shell does not call any scoring, question-generation, or draft-generation endpoints. No LLM calls are made. No job descriptions are saved. No CV content is generated.
        </p>
        <p class="mt-3 text-sm leading-6 text-amber-800">
          To run the full apply flow, use the legacy interface at
          <code class="rounded bg-amber-100 px-1 font-mono text-xs">/ui/apply</code>.
        </p>
      </div>

      <!-- Future steps summary -->
      <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Future steps</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          When this page is fully migrated, the apply flow will run entirely within Vue without redirecting to a legacy page.
        </p>

        <ol class="mt-4 space-y-3">
          <li
            v-for="step in steps"
            :key="step.number"
            class="flex items-start gap-3 text-sm"
          >
            <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-xs font-semibold text-slate-400">
              {{ step.number }}
            </span>
            <span class="text-slate-600">
              <span class="font-medium text-slate-700">{{ step.title }}</span>
              — not yet active
            </span>
          </li>
        </ol>
      </div>
    </aside>
  </section>
</template>
