<script setup>
import StatusMessage from "./StatusMessage.vue";

defineProps({
  review: { type: Object, required: true },
  hasQuestions: { type: Boolean, default: false },
});

const emit = defineEmits(["back"]);
</script>

<template>
  <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
    <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Review</p>
        <h2 class="mt-1 text-2xl font-semibold text-slate-950">Review your extracted profile</h2>
        <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Check the facts Job Agent extracted before the search focus step. Edit anything that is
          incomplete, too vague, or incorrectly grouped.
        </p>
      </div>
      <a class="text-sm font-semibold text-sky-700 hover:text-sky-800" href="/ui/onboarding">
        Finish setup in legacy UI
      </a>
    </div>

    <div
      v-if="review.readinessBanner.value"
      class="mt-5 rounded-md border px-4 py-3 text-sm"
      :class="review.readinessBanner.value.tone"
    >
      <p class="font-semibold">{{ review.readinessBanner.value.title }}</p>
      <p class="mt-1">{{ review.readinessBanner.value.message }}</p>
    </div>

    <div
      v-if="review.reviewBusy.value"
      class="mt-6 space-y-3 rounded-md border border-slate-200 bg-slate-50 p-4"
      aria-busy="true"
      aria-label="Loading profile review"
    >
      <div class="h-5 w-48 animate-pulse rounded bg-slate-200"></div>
      <div class="h-4 w-full animate-pulse rounded bg-slate-200"></div>
      <div class="h-4 w-3/4 animate-pulse rounded bg-slate-200"></div>
    </div>

    <div v-else-if="!review.reviewFactSheet.value" class="mt-6 rounded-md border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
      Your extracted profile review will appear here after intake finishes.
    </div>

    <div v-else class="mt-6 space-y-6">
      <section class="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <p class="text-sm font-semibold text-slate-900">Identity</p>
        <div class="mt-3 grid gap-4 md:grid-cols-2">
          <label class="block">
            <span class="text-sm font-medium text-slate-700">Full name</span>
            <input
              v-model.trim="review.reviewForm.value.fullName"
              class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
              type="text"
              :disabled="review.reviewSaving.value"
            />
          </label>
          <label class="block">
            <span class="text-sm font-medium text-slate-700">Email</span>
            <input
              v-model.trim="review.reviewForm.value.email"
              class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
              type="email"
              :disabled="review.reviewSaving.value"
            />
          </label>
        </div>
      </section>

      <section class="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <div class="flex items-center justify-between gap-3">
          <h3 class="text-base font-semibold text-slate-950">Education</h3>
          <button
            type="button"
            class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            :disabled="review.reviewSaving.value"
            @click="review.addReviewRow('education')"
          >
            Add education
          </button>
        </div>

        <div class="mt-4 space-y-3">
          <div
            v-for="(row, index) in review.reviewForm.value.education"
            :key="`education-${index}`"
            class="grid gap-3 rounded-md border border-slate-200 bg-white p-3 md:grid-cols-2"
          >
            <input v-model.trim="row.degree" class="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Degree" :disabled="review.reviewSaving.value" />
            <input v-model.trim="row.field" class="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Field" :disabled="review.reviewSaving.value" />
            <input v-model.trim="row.institution" class="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Institution" :disabled="review.reviewSaving.value" />
            <div class="flex gap-2">
              <input v-model.trim="row.status" class="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Status" :disabled="review.reviewSaving.value" />
              <button
                type="button"
                class="rounded-md border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50"
                :disabled="review.reviewSaving.value"
                @click="review.removeReviewRow('education', index)"
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      </section>

      <section class="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <div class="flex items-center justify-between gap-3">
          <h3 class="text-base font-semibold text-slate-950">Experience</h3>
          <button
            type="button"
            class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            :disabled="review.reviewSaving.value"
            @click="review.addReviewRow('experience')"
          >
            Add experience
          </button>
        </div>

        <div class="mt-4 space-y-3">
          <div
            v-for="(row, index) in review.reviewForm.value.experience"
            :key="`experience-${index}`"
            class="space-y-3 rounded-md border border-slate-200 bg-white p-3"
          >
            <div class="grid gap-3 md:grid-cols-2">
              <input v-model.trim="row.role_title" class="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Role title" :disabled="review.reviewSaving.value" />
              <input v-model.trim="row.organization" class="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Organization" :disabled="review.reviewSaving.value" />
              <input v-model.trim="row.start_date" class="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Start date" :disabled="review.reviewSaving.value" />
              <input v-model.trim="row.end_date" class="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="End date" :disabled="review.reviewSaving.value" />
            </div>
            <textarea
              v-model="row.responsibilities_text"
              class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              rows="4"
              placeholder="Responsibilities, one per line"
              :disabled="review.reviewSaving.value"
            ></textarea>
            <button
              type="button"
              class="rounded-md border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50"
              :disabled="review.reviewSaving.value"
              @click="review.removeReviewRow('experience', index)"
            >
              Remove experience
            </button>
          </div>
        </div>
      </section>

      <section class="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <div class="flex items-center justify-between gap-3">
          <h3 class="text-base font-semibold text-slate-950">Projects and evidence</h3>
          <button
            type="button"
            class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            :disabled="review.reviewSaving.value"
            @click="review.addReviewRow('projects')"
          >
            Add evidence
          </button>
        </div>

        <div class="mt-4 space-y-3">
          <div
            v-for="(row, index) in review.reviewForm.value.projects"
            :key="`project-${index}`"
            class="space-y-3 rounded-md border border-slate-200 bg-white p-3"
          >
            <div class="grid gap-3 md:grid-cols-2">
              <input v-model.trim="row.name" class="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Title" :disabled="review.reviewSaving.value" />
              <input v-model.trim="row.link" class="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Link" :disabled="review.reviewSaving.value" />
            </div>
            <textarea
              v-model="row.summary"
              class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              rows="3"
              placeholder="Summary and evidence"
              :disabled="review.reviewSaving.value"
            ></textarea>
            <button
              type="button"
              class="rounded-md border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50"
              :disabled="review.reviewSaving.value"
              @click="review.removeReviewRow('projects', index)"
            >
              Remove project
            </button>
          </div>
        </div>
      </section>

      <section class="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <h3 class="text-base font-semibold text-slate-950">Skills and languages</h3>
        <textarea
          v-model="review.reviewForm.value.skillsText"
          class="mt-3 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          rows="5"
          placeholder="One skill per line"
          :disabled="review.reviewSaving.value"
        ></textarea>
      </section>

      <section class="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <div class="flex items-center justify-between gap-3">
          <h3 class="text-base font-semibold text-slate-950">Languages</h3>
          <button
            type="button"
            class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            :disabled="review.reviewSaving.value"
            @click="review.addReviewLanguage"
          >
            Add language
          </button>
        </div>
        <div class="mt-4 space-y-3">
          <div
            v-for="(row, index) in review.reviewForm.value.languages"
            :key="`language-${index}`"
            class="grid gap-3 rounded-md border border-slate-200 bg-white p-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]"
          >
            <input v-model.trim="row.name" class="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Language" :disabled="review.reviewSaving.value" />
            <input v-model.trim="row.level" class="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Level" :disabled="review.reviewSaving.value" />
            <button
              type="button"
              class="rounded-md border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50"
              :disabled="review.reviewSaving.value"
              @click="review.removeReviewLanguage(index)"
            >
              Remove
            </button>
          </div>
        </div>
      </section>

      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <StatusMessage
          :message="review.reviewStatus.value"
          :is-error="review.reviewStatusError.value"
        />
        <div class="flex gap-3">
          <button
            type="button"
            class="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="review.reviewSaving.value"
            @click="emit('back')"
          >
            Back
          </button>
          <button
            type="button"
            class="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            :disabled="review.reviewSaving.value"
            @click="review.saveProfileReview"
          >
            {{ review.reviewSaving.value ? "Saving..." : "Save profile review" }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
