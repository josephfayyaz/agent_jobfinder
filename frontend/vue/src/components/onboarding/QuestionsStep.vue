<script setup>
import StatusMessage from "./StatusMessage.vue";

defineProps({
  questions: { type: Object, required: true },
});

const emit = defineEmits(["back"]);
</script>

<template>
  <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
    <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Questions</p>
        <h2 class="mt-1 text-2xl font-semibold text-slate-950">Answer only what is missing</h2>
        <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Short answers are enough. Skip anything you cannot confirm truthfully unless it is marked as required.
        </p>
      </div>
    </div>

    <div
      v-if="!questions.normalizedQuestions.value.length"
      class="mt-6 rounded-md border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600"
    >
      No follow-up questions are loaded. Return to the Facts step to run intake.
    </div>

    <div v-else class="mt-6 space-y-5">
      <div
        v-for="(question, questionIndex) in questions.normalizedQuestions.value"
        :key="question.id"
        class="rounded-md border border-slate-200 bg-slate-50 p-4"
      >
        <div class="flex flex-col gap-1">
          <label class="text-sm font-semibold text-slate-900" :for="`answer-${question.id}`">
            {{ question.prompt }}
          </label>
          <p v-if="question.required" class="text-xs font-semibold uppercase tracking-wide text-amber-700">
            Required to build a usable fact sheet
          </p>
        </div>

        <div v-if="question.kind === 'single_select'" class="mt-3 space-y-2">
          <label
            v-for="(option, optionIndex) in question.options"
            :key="`${question.id}-${option}`"
            class="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
            :for="`answer-${question.id}-${optionIndex}`"
          >
            <input
              :id="`answer-${question.id}-${optionIndex}`"
              v-model="questions.questionAnswers.value[question.id].selected"
              type="radio"
              :name="`answer-${question.id}`"
              :value="option"
              :disabled="questions.questionsBusy.value"
            />
            <span>{{ option }}</span>
          </label>
        </div>

        <div v-if="question.kind === 'multi_select'" class="mt-3 space-y-2">
          <label
            v-for="(option, optionIndex) in question.options"
            :key="`${question.id}-${option}`"
            class="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
            :for="`answer-${question.id}-${optionIndex}`"
          >
            <input
              :id="`answer-${question.id}-${optionIndex}`"
              v-model="questions.questionAnswers.value[question.id].choices"
              type="checkbox"
              :value="option"
              :disabled="questions.questionsBusy.value"
            />
            <span>{{ option }}</span>
          </label>
        </div>

        <textarea
          v-if="question.kind === 'text' || question.allow_free_text"
          :id="`answer-${question.id}`"
          v-model="questions.questionAnswers.value[question.id].text"
          class="mt-3 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          :rows="question.kind === 'text' ? 3 : 2"
          :placeholder="question.kind === 'text' ? 'Type your answer' : 'Optional note'"
          :disabled="questions.questionsBusy.value"
        ></textarea>

        <p class="mt-3 text-xs text-slate-500">
          Question {{ questionIndex + 1 }} of {{ questions.normalizedQuestions.value.length }}
        </p>
      </div>

      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <StatusMessage
          :message="questions.questionsStatus.value"
          :is-error="questions.questionsStatusError.value"
        />
        <div class="flex gap-3">
          <button
            type="button"
            class="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="questions.questionsBusy.value"
            @click="emit('back')"
          >
            Back
          </button>
          <button
            type="button"
            class="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            :disabled="questions.questionsBusy.value"
            @click="questions.submitQuestionAnswers"
          >
            {{ questions.questionsBusy.value ? "Saving..." : "Save answers" }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
