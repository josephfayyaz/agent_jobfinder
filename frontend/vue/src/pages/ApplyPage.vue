<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";
import { vueApiFetch } from "../api/client";

const router = useRouter();

const jobDescription = ref("");
const selectedTrackSlug = ref("");
const scoreLoading = ref(false);
const questionsLoading = ref(false);
const draftLoading = ref(false);
const polling = ref(false);
const errorMessage = ref("");
const scoreResult = ref(null);
const questions = ref([]);
const answers = ref({});
const taskId = ref("");
const draftId = ref("");
const pollingMessage = ref("Waiting for worker...");
const statusText = ref("");
const setupRequired = ref(false);
const setupRequiredMessage = ref("");

let pollTimer = null;
let pollErrors = 0;

const canScore = computed(() => jobDescription.value.trim().length > 0 && !scoreLoading.value && !questionsLoading.value && !draftLoading.value && !polling.value);
const canGenerateQuestions = computed(() => !!scoreResult.value && !scoreLoading.value && !questionsLoading.value && !draftLoading.value && !polling.value);
const canGenerateDraft = computed(() => !!scoreResult.value && !!selectedTrackSlug.value && !scoreLoading.value && !questionsLoading.value && !draftLoading.value && !polling.value);

const trackOptions = computed(() => {
  const items = scoreResult.value?.track_options;
  return Array.isArray(items) ? items.filter((item) => item?.slug) : [];
});
const matchedSkills = computed(() => {
  const items = scoreResult.value?.matched_skills;
  return Array.isArray(items) ? items.filter(Boolean) : [];
});
const gaps = computed(() => {
  const items = scoreResult.value?.gaps;
  return Array.isArray(items) ? items.filter(Boolean) : [];
});
const scoreValue = computed(() => (typeof scoreResult.value?.score === "number" ? scoreResult.value.score : null));
const jobData = computed(() => scoreResult.value?.job_data ?? null);
const hasQuestions = computed(() => questions.value.length > 0);
const hasTask = computed(() => Boolean(taskId.value));

function stopPolling() {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
  polling.value = false;
}

function resetFollowupState() {
  stopPolling();
  selectedTrackSlug.value = "";
  questions.value = [];
  answers.value = {};
  taskId.value = "";
  draftId.value = "";
  pollingMessage.value = "Waiting for worker...";
  statusText.value = "";
}

function setDefaultTrack() {
  if (!selectedTrackSlug.value && trackOptions.value.length > 0) {
    selectedTrackSlug.value = String(trackOptions.value[0].slug || "");
  }
}

async function scoreJob() {
  if (!canScore.value) {
    return;
  }

  scoreLoading.value = true;
  errorMessage.value = "";
  setupRequired.value = false;
  setupRequiredMessage.value = "";
  scoreResult.value = null;
  resetFollowupState();

  try {
    const payload = await vueApiFetch("/apply/score", {
      method: "POST",
      body: JSON.stringify({ job_description: jobDescription.value.trim() }),
    });
    scoreResult.value = payload.data ?? {};
    setDefaultTrack();
  } catch (err) {
    if (err?.code === "setup_required") {
      setupRequired.value = true;
      setupRequiredMessage.value = err instanceof Error ? err.message : "Use the setup flow to create a candidate profile and choose target roles before generating a tailored CV draft.";
    } else {
      errorMessage.value = err instanceof Error ? err.message : "Unable to score this job right now.";
    }
  } finally {
    scoreLoading.value = false;
  }
}

async function loadQuestions() {
  if (!canGenerateQuestions.value || !jobData.value) {
    return;
  }

  questionsLoading.value = true;
  errorMessage.value = "";
  questions.value = [];
  answers.value = {};

  try {
    const payload = await vueApiFetch("/apply/questions", {
      method: "POST",
      body: JSON.stringify({
        job_data: jobData.value,
        gaps: gaps.value,
        answers: answers.value,
      }),
    });
    questions.value = Array.isArray(payload.data?.questions) ? payload.data.questions.filter(Boolean) : [];
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : "Unable to generate questions right now.";
  } finally {
    questionsLoading.value = false;
  }
}

async function pollTaskStatus(currentTaskId) {
  try {
    const payload = await vueApiFetch(`/apply/status/${currentTaskId}`);
    pollErrors = 0;
    const data = payload.data ?? {};
    const nextStatus = String(data.status || "pending");
    const nextDraftId = String(data.draft_id || "");

    statusText.value = `Status: ${nextStatus}`;
    pollingMessage.value = String(data.message || "Waiting for worker...");

    if (nextStatus === "completed" && nextDraftId) {
      draftId.value = nextDraftId;
      stopPolling();
      await router.push(`/drafts/${nextDraftId}`);
      return;
    }

    if (nextStatus === "failed") {
      stopPolling();
      errorMessage.value = String(data.message || "Draft generation failed.");
    }
  } catch (err) {
    pollErrors += 1;
    if (pollErrors >= 3) {
      stopPolling();
      errorMessage.value = err instanceof Error ? err.message : "Status check failed. Make sure the worker is running.";
    }
  }
}

function beginPolling(currentTaskId) {
  stopPolling();
  polling.value = true;
  pollErrors = 0;
  pollingMessage.value = "Task queued. Waiting for worker...";
  statusText.value = "Status: pending";
  pollTimer = window.setInterval(() => {
    void pollTaskStatus(currentTaskId);
  }, 3000);
  void pollTaskStatus(currentTaskId);
}

async function generateDraft() {
  if (!canGenerateDraft.value || !jobData.value) {
    return;
  }

  draftLoading.value = true;
  errorMessage.value = "";
  taskId.value = "";
  draftId.value = "";

  try {
    const payload = await vueApiFetch("/apply/draft", {
      method: "POST",
      body: JSON.stringify({
        job_data: jobData.value,
        questions: questions.value,
        answers: answers.value,
        track_slug: selectedTrackSlug.value,
      }),
    });
    taskId.value = String(payload.data?.task_id || "");
    if (!taskId.value) {
      throw new Error("Draft generation did not return a task ID.");
    }
    beginPolling(taskId.value);
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : "Unable to generate a draft right now.";
  } finally {
    draftLoading.value = false;
  }
}

function updateAnswer(questionId, value) {
  answers.value = {
    ...answers.value,
    [questionId]: value,
  };
}

onBeforeUnmount(() => {
  stopPolling();
});
</script>

<template>
  <AppPageHeader
    title="Apply"
    description="Paste a job description, review the match, ask clarifying questions, and generate a draft without leaving the Vue app."
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <div class="space-y-6 lg:col-span-2">
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Apply workflow</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
          Paste the job description
        </h2>
        <p class="mt-3 text-sm leading-6 text-slate-600">
          Draft generation only starts after you click Generate Draft. Generated drafts remain reviewable before approval. No application is submitted from this page.
        </p>

        <label for="apply-job-description" class="mt-6 block text-sm font-medium text-slate-700">
          Job description
        </label>
        <textarea
          id="apply-job-description"
          v-model="jobDescription"
          rows="10"
          placeholder="Paste the job description here..."
          class="mt-2 w-full resize-y rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 shadow-sm focus:border-slate-950 focus:outline-none focus:ring-2 focus:ring-slate-200"
        />

        <div class="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            :disabled="!canScore"
            class="rounded-xl bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            @click="scoreJob"
          >
            {{ scoreLoading ? "Scoring..." : "Score" }}
          </button>
          <a
            href="/ui/apply"
            class="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
          >
            Legacy fallback: /ui/apply
          </a>
        </div>
      </article>

      <article
        v-if="setupRequired"
        class="rounded-2xl border border-amber-200 bg-amber-50 p-6 shadow-sm"
      >
        <p class="text-sm font-medium text-amber-900">Setup required before applying</p>
        <p class="mt-2 text-sm leading-6 text-amber-800">
          {{ setupRequiredMessage || "Use the setup flow to create a candidate profile and choose target roles before generating a tailored CV draft." }}
        </p>

        <div class="mt-4 flex flex-wrap gap-3">
          <RouterLink
            to="/onboarding"
            class="rounded-xl bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
          >
            Go to Onboarding
          </RouterLink>
          <RouterLink
            to="/settings"
            class="rounded-xl border border-amber-300 bg-white px-4 py-2 text-sm font-medium text-amber-900 transition hover:bg-amber-100"
          >
            Open Settings
          </RouterLink>
          <a
            href="/ui/apply"
            class="self-center text-sm font-medium text-amber-900 underline decoration-amber-300 underline-offset-4 hover:decoration-amber-500"
          >
            Legacy apply fallback
          </a>
        </div>
      </article>

      <article v-if="errorMessage" class="rounded-2xl border border-rose-200 bg-rose-50 p-6 shadow-sm">
        <p class="text-sm font-medium text-rose-900">Something needs attention</p>
        <p class="mt-2 text-sm leading-6 text-rose-800">{{ errorMessage }}</p>
      </article>

      <article v-if="scoreResult" class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p class="text-sm font-medium text-slate-500">Step 2</p>
            <h2 class="mt-1 text-xl font-semibold tracking-tight text-slate-950">Score result</h2>
          </div>
          <div class="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white">
            {{ scoreValue === null ? "Score unavailable" : `${scoreValue}/100` }}
          </div>
        </div>

        <p class="mt-3 text-sm leading-6 text-slate-600">
          {{ scoreResult.summary || "Review the parsed job data and decide whether you want clarifying questions before generating a draft." }}
        </p>

        <div class="mt-6 grid gap-4 md:grid-cols-2">
          <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <p class="text-xs font-semibold uppercase text-emerald-800">Matched skills</p>
            <ul v-if="matchedSkills.length" class="mt-3 space-y-2 text-sm text-emerald-950">
              <li v-for="skill in matchedSkills" :key="skill">{{ skill }}</li>
            </ul>
            <p v-else class="mt-3 text-sm text-emerald-900">No matched skills were returned.</p>
          </div>

          <div class="rounded-xl border border-amber-200 bg-amber-50 p-4">
            <p class="text-xs font-semibold uppercase text-amber-900">Gaps</p>
            <ul v-if="gaps.length" class="mt-3 space-y-2 text-sm text-amber-950">
              <li v-for="gap in gaps" :key="gap">{{ gap }}</li>
            </ul>
            <p v-else class="mt-3 text-sm text-amber-900">No major gaps were detected, so you can generate a draft directly.</p>
          </div>
        </div>

        <div class="mt-6 grid gap-4 md:grid-cols-2">
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-semibold uppercase text-slate-500">Parsed title</p>
            <p class="mt-2 text-sm font-medium text-slate-950">{{ jobData?.title || "Unknown title" }}</p>
          </div>
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-semibold uppercase text-slate-500">Parsed company</p>
            <p class="mt-2 text-sm font-medium text-slate-950">{{ jobData?.company || "Unknown company" }}</p>
          </div>
        </div>

        <div class="mt-6">
          <label for="apply-track-select" class="block text-sm font-medium text-slate-700">
            Resume track
          </label>
          <select
            id="apply-track-select"
            v-model="selectedTrackSlug"
            class="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 shadow-sm focus:border-slate-950 focus:outline-none focus:ring-2 focus:ring-slate-200"
          >
            <option disabled value="">Select a resume track</option>
            <option v-for="track in trackOptions" :key="track.slug" :value="track.slug">
              {{ track.title }}
            </option>
          </select>
          <p class="mt-2 text-xs text-slate-500">
            Choose the resume track you want the draft workflow to use.
          </p>
        </div>

        <div class="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            :disabled="!canGenerateQuestions"
            class="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            @click="loadQuestions"
          >
            {{ questionsLoading ? "Generating questions..." : "Generate Questions" }}
          </button>
          <button
            type="button"
            :disabled="!canGenerateDraft"
            class="rounded-xl bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            @click="generateDraft"
          >
            {{ draftLoading ? "Queueing draft..." : "Generate Draft" }}
          </button>
        </div>
      </article>

      <article v-if="scoreResult" class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Step 3</p>
        <h2 class="mt-1 text-xl font-semibold tracking-tight text-slate-950">Clarifying questions</h2>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          These answers are optional. They only help the draft workflow fill evidence gaps more accurately.
        </p>

        <div v-if="questionsLoading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Generating clarifying questions...
        </div>

        <div v-else-if="hasQuestions" class="mt-4 space-y-4">
          <article
            v-for="(question, index) in questions"
            :key="question.id || `question-${index}`"
            class="rounded-xl border border-slate-200 bg-slate-50 p-4"
          >
            <p class="text-xs font-semibold uppercase text-slate-500">
              Gap: {{ question.gap || `Question ${index + 1}` }}
            </p>
            <p class="mt-2 text-sm font-medium text-slate-950">
              {{ question.question || "Clarification requested" }}
            </p>
            <p v-if="question.why" class="mt-2 text-xs italic text-slate-500">
              {{ question.why }}
            </p>
            <textarea
              :value="answers[String(question.id || `q${index}`)] || ''"
              rows="3"
              class="mt-3 w-full resize-y rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-slate-950 focus:outline-none focus:ring-2 focus:ring-slate-200"
              placeholder="Add any evidence you want the draft workflow to consider."
              @input="updateAnswer(String(question.id || `q${index}`), $event.target.value)"
            />
          </article>
        </div>

        <div v-else class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600">
          No clarifying questions have been returned yet. If the gaps look clear enough, you can generate a draft directly.
        </div>
      </article>

      <article v-if="hasTask || polling" class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Step 4</p>
        <h2 class="mt-1 text-xl font-semibold tracking-tight text-slate-950">Draft generation status</h2>

        <div class="mt-4 flex items-center gap-3">
          <div class="h-8 w-8 rounded-full border-4 border-slate-200 border-t-slate-950" :class="polling ? 'animate-spin' : ''"></div>
          <div>
            <p class="text-sm font-medium text-slate-950">{{ pollingMessage }}</p>
            <p class="text-xs text-slate-500">{{ statusText || "Waiting for the first status update..." }}</p>
          </div>
        </div>

        <dl class="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-2">
          <div>
            <dt class="text-slate-500">Task ID</dt>
            <dd class="mt-1 font-mono text-slate-950 break-all">{{ taskId || "Not started" }}</dd>
          </div>
          <div>
            <dt class="text-slate-500">Draft ID</dt>
            <dd class="mt-1 font-mono text-slate-950 break-all">{{ draftId || "Pending" }}</dd>
          </div>
        </dl>
      </article>
    </div>

    <aside class="space-y-4">
      <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">How this behaves</p>
        <ul class="mt-3 space-y-3 text-sm leading-6 text-slate-600">
          <li>Scoring only runs after you click Score.</li>
          <li>Question generation only runs after you click Generate Questions.</li>
          <li>Draft generation only runs after you click Generate Draft.</li>
          <li>Completion sends you to the Vue draft detail route, not the legacy UI.</li>
        </ul>
      </div>

      <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Current state</p>
        <dl class="mt-3 space-y-3 text-sm">
          <div class="flex items-start justify-between gap-4">
            <dt class="text-slate-500">Score result</dt>
            <dd class="font-medium text-slate-950">{{ scoreResult ? "Ready" : "Not yet" }}</dd>
          </div>
          <div class="flex items-start justify-between gap-4">
            <dt class="text-slate-500">Questions</dt>
            <dd class="font-medium text-slate-950">{{ hasQuestions ? questions.length : 0 }}</dd>
          </div>
          <div class="flex items-start justify-between gap-4">
            <dt class="text-slate-500">Polling</dt>
            <dd class="font-medium text-slate-950">{{ polling ? "Active" : "Idle" }}</dd>
          </div>
          <div class="flex items-start justify-between gap-4">
            <dt class="text-slate-500">Track selected</dt>
            <dd class="font-medium text-slate-950">{{ selectedTrackSlug || "No" }}</dd>
          </div>
        </dl>
      </div>
    </aside>
  </section>
</template>
