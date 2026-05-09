<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";
import { vueApiFetch } from "../api/client";

const route = useRoute();
const draftId = computed(() => String(route.params.id || ""));

const loading = ref(true);
const error = ref("");
const payload = ref(null);
const coverLetter = ref("");
const coverLetterSubject = ref("");
const coverLetterError = ref("");
const actionMessage = ref("");
const actionLoading = ref(false);
const coverLetterLoading = ref(false);

onMounted(async () => {
  if (!draftId.value) {
    error.value = "No draft ID provided in route.";
    loading.value = false;
    return;
  }
  try {
    payload.value = await vueApiFetch(`/drafts/${draftId.value}`);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});

const responseData = computed(() => payload.value?.data ?? {});
const responseStatus = computed(() => payload.value?.status ?? "");
const responseMessage = computed(() => payload.value?.message ?? "");
const isPlaceholder = computed(() => responseStatus.value === "placeholder");
const detail = computed(() => responseData.value.item ?? {});
const linkedJob = computed(() => detail.value?.job ?? null);
const linkedApplication = computed(() => detail.value?.application ?? null);
const companyRecord = computed(() => detail.value?.company_record ?? null);

const detailLabel = computed(() => (
  detail.value?.title
  || linkedJob.value?.title
  || detail.value?.role
  || (draftId.value ? `Draft ${draftId.value.slice(0, 8)}` : "Untitled draft")
));
const detailCompany = computed(() => detail.value?.company || linkedJob.value?.company || "Unknown company");
const detailLocation = computed(() => detail.value?.location || linkedJob.value?.location || "");
const detailStatus = computed(() => detail.value?.status || "Status unavailable");
const detailScore = computed(() => (typeof detail.value?.score === "number" ? detail.value.score : null));
const detailApproved = computed(() => (typeof detail.value?.approved === "boolean" ? detail.value.approved : null));
const detailProvider = computed(() => detail.value?.provider || "");
const detailHasContent = computed(() => detail.value?.has_content ?? false);
const detailHasCoverLetter = computed(() => detail.value?.has_cover_letter ?? false);
const detailCreatedAt = computed(() => detail.value?.created_at || "");
const detailUpdatedAt = computed(() => detail.value?.updated_at || "");
const linkedJobSource = computed(() => linkedJob.value?.source || "");
const linkedJobStatus = computed(() => linkedJob.value?.status || "");
const linkedJobId = computed(() => linkedJob.value?.id || "");
const linkedApplicationId = computed(() => linkedApplication.value?.id || detail.value?.application_id || "");
const linkedApplicationStatus = computed(() => linkedApplication.value?.status || "");
const companyRecordName = computed(() => companyRecord.value?.name || "");
const companyRecordId = computed(() => companyRecord.value?.id || "");
const companyRecordUrlAvailable = computed(() => companyRecord.value?.career_page_url_available === true);
const linkedJobTarget = computed(() => (
  linkedJobId.value ? `/jobs/${linkedJobId.value}` : "/jobs"
));
const linkedApplicationTarget = computed(() => (
  linkedApplicationId.value ? `/applications/${linkedApplicationId.value}` : "/applications"
));
const linkedJobLinkLabel = computed(() => (
  linkedJobId.value ? "View linked job" : "View jobs"
));
const linkedApplicationLinkLabel = computed(() => (
  linkedApplicationId.value ? "View linked application" : "View applications"
));

async function updateDraftAction(action) {
  if (!draftId.value || actionLoading.value) {
    return;
  }

  const confirmationText = action === "approve"
    ? "Approve this draft for submission readiness?"
    : "Reject this draft and remove its approved state?";

  if (!window.confirm(confirmationText)) {
    return;
  }

  actionLoading.value = true;
  actionMessage.value = "";
  error.value = "";

  try {
    const actionPayload = await vueApiFetch(`/drafts/${draftId.value}/${action}`, {
      method: "POST",
      body: JSON.stringify({ user_confirmed: true }),
    });
    const updated = actionPayload.data ?? {};
    payload.value = {
      ...(payload.value || {}),
      data: {
        ...(responseData.value || {}),
        item: {
          ...detail.value,
          approved: updated.approved,
          status: updated.status,
        },
      },
    };
    actionMessage.value = action === "approve" ? "Draft approved." : "Draft rejected.";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Draft action failed.";
  } finally {
    actionLoading.value = false;
  }
}

async function generateCoverLetter() {
  if (!draftId.value || coverLetterLoading.value) {
    return;
  }

  coverLetterLoading.value = true;
  coverLetterError.value = "";
  actionMessage.value = "";

  try {
    const result = await vueApiFetch(`/drafts/${draftId.value}/cover-letter`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    const data = result.data ?? {};
    coverLetter.value = String(data.cover_letter || "");
    coverLetterSubject.value = String(data.subject || "");
    payload.value = {
      ...(payload.value || {}),
      data: {
        ...(responseData.value || {}),
        item: {
          ...detail.value,
          has_cover_letter: true,
        },
      },
    };
    actionMessage.value = "Cover letter ready.";
  } catch (err) {
    coverLetterError.value = err instanceof Error ? err.message : "Cover letter generation failed.";
  } finally {
    coverLetterLoading.value = false;
  }
}
</script>

<template>
  <AppPageHeader
    title="Draft Detail"
    :description="`Review and act on draft ${draftId || '(unknown)'}.`"
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <div class="space-y-6 lg:col-span-2">
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Draft metadata</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
          {{ detailLabel }}
        </h2>

        <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Loading draft...
        </div>

        <div v-else-if="error" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          {{ error }}
        </div>

        <div v-else class="mt-4 space-y-4">
          <p v-if="responseMessage" class="text-sm leading-6 text-slate-600">
            {{ responseMessage }}
          </p>

          <div
            v-if="isPlaceholder"
            class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
          >
            The backend is still returning placeholder draft data. The detail below is rendered safely from whatever is available.
          </div>

          <div v-if="actionMessage" class="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
            {{ actionMessage }}
          </div>

          <dl class="grid gap-4 text-sm md:grid-cols-2">
            <div>
              <dt class="text-slate-500">Route ID</dt>
              <dd class="mt-1 font-mono text-slate-950 break-all">{{ draftId || "Not provided" }}</dd>
            </div>
            <div>
              <dt class="text-slate-500">Status</dt>
              <dd class="mt-1 font-medium text-slate-950">{{ detailStatus }}</dd>
            </div>
            <div>
              <dt class="text-slate-500">Company</dt>
              <dd class="mt-1 text-slate-950">{{ detailCompany }}</dd>
            </div>
            <div v-if="detailLocation">
              <dt class="text-slate-500">Location</dt>
              <dd class="mt-1 text-slate-950">{{ detailLocation }}</dd>
            </div>
            <div v-if="detailScore !== null">
              <dt class="text-slate-500">Score</dt>
              <dd class="mt-1 font-semibold text-slate-950">{{ detailScore }}</dd>
            </div>
            <div v-if="detailApproved !== null">
              <dt class="text-slate-500">Approved</dt>
              <dd class="mt-1 text-slate-950">{{ detailApproved ? "Yes" : "No" }}</dd>
            </div>
            <div v-if="detailProvider">
              <dt class="text-slate-500">Provider</dt>
              <dd class="mt-1 text-slate-950">{{ detailProvider }}</dd>
            </div>
            <div>
              <dt class="text-slate-500">Has content</dt>
              <dd class="mt-1 text-slate-950">{{ detailHasContent ? "Yes" : "No" }}</dd>
            </div>
            <div>
              <dt class="text-slate-500">Has cover letter</dt>
              <dd class="mt-1 text-slate-950">{{ detailHasCoverLetter ? "Yes" : "No" }}</dd>
            </div>
            <div v-if="detailCreatedAt">
              <dt class="text-slate-500">Created</dt>
              <dd class="mt-1 text-slate-950">{{ detailCreatedAt }}</dd>
            </div>
            <div v-if="detailUpdatedAt">
              <dt class="text-slate-500">Updated</dt>
              <dd class="mt-1 text-slate-950">{{ detailUpdatedAt }}</dd>
            </div>
          </dl>
        </div>
      </article>

      <article v-if="linkedJob || companyRecord" class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Linked job metadata</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">Job and company context</h2>

        <div class="mt-4 grid gap-4 text-sm md:grid-cols-2">
          <div v-if="linkedJob" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-semibold uppercase text-slate-500">Job</p>
            <dl class="mt-3 space-y-3">
              <div v-if="linkedJobId" class="flex items-start justify-between gap-4">
                <dt class="text-slate-500">Job ID</dt>
                <dd class="font-mono text-xs text-slate-950 break-all">{{ linkedJobId }}</dd>
              </div>
              <div v-if="linkedJob.title" class="flex items-start justify-between gap-4">
                <dt class="text-slate-500">Title</dt>
                <dd class="text-right text-slate-950">{{ linkedJob.title }}</dd>
              </div>
              <div v-if="linkedJob.company" class="flex items-start justify-between gap-4">
                <dt class="text-slate-500">Company</dt>
                <dd class="text-right text-slate-950">{{ linkedJob.company }}</dd>
              </div>
              <div v-if="linkedJob.location" class="flex items-start justify-between gap-4">
                <dt class="text-slate-500">Location</dt>
                <dd class="text-right text-slate-950">{{ linkedJob.location }}</dd>
              </div>
              <div v-if="linkedJobStatus" class="flex items-start justify-between gap-4">
                <dt class="text-slate-500">Job status</dt>
                <dd class="text-right text-slate-950">{{ linkedJobStatus }}</dd>
              </div>
              <div v-if="linkedJobSource" class="flex items-start justify-between gap-4">
                <dt class="text-slate-500">Source</dt>
                <dd class="text-right text-slate-950">{{ linkedJobSource }}</dd>
              </div>
            </dl>
          </div>

          <div v-if="companyRecord" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-semibold uppercase text-slate-500">Company record</p>
            <dl class="mt-3 space-y-3">
              <div v-if="companyRecordId" class="flex items-start justify-between gap-4">
                <dt class="text-slate-500">Record ID</dt>
                <dd class="font-mono text-xs text-slate-950 break-all">{{ companyRecordId }}</dd>
              </div>
              <div v-if="companyRecordName" class="flex items-start justify-between gap-4">
                <dt class="text-slate-500">Name</dt>
                <dd class="text-right text-slate-950">{{ companyRecordName }}</dd>
              </div>
              <div class="flex items-start justify-between gap-4">
                <dt class="text-slate-500">Career page stored</dt>
                <dd class="text-right text-slate-950">{{ companyRecordUrlAvailable ? "Yes" : "No" }}</dd>
              </div>
            </dl>
          </div>
        </div>
      </article>

      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Review actions</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">Approve, reject, or generate a cover letter</h2>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          Approve and reject require confirmation. Cover letter generation only runs after you click the button below.
        </p>

        <div class="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            class="rounded-xl bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            :disabled="loading || actionLoading"
            @click="updateDraftAction('approve')"
          >
            {{ actionLoading ? "Working..." : "Approve Draft" }}
          </button>
          <button
            type="button"
            class="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="loading || actionLoading"
            @click="updateDraftAction('reject')"
          >
            {{ actionLoading ? "Working..." : "Reject Draft" }}
          </button>
          <button
            type="button"
            class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="loading || coverLetterLoading"
            @click="generateCoverLetter"
          >
            {{ coverLetterLoading ? "Generating cover letter..." : "Generate Cover Letter" }}
          </button>
        </div>

        <div v-if="coverLetterError" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          {{ coverLetterError }}
        </div>
      </article>

      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Cover letter</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">Generated output</h2>

        <div v-if="coverLetterLoading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Generating cover letter...
        </div>

        <div v-else-if="coverLetter" class="mt-4 space-y-4">
          <div v-if="coverLetterSubject" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-semibold uppercase text-slate-500">Subject</p>
            <p class="mt-2 text-sm font-medium text-slate-950">{{ coverLetterSubject }}</p>
          </div>
          <pre class="whitespace-pre-wrap rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-800">{{ coverLetter }}</pre>
        </div>

        <div v-else class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600">
          No cover letter has been generated in this Vue session yet.
        </div>
      </article>

      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Future actions</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">Still deferred</h2>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          Revise, polish, clarify, preview updates, bullet rewrite, and inferred additions stay out of scope for this migration step.
        </p>

        <div class="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            disabled
            class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-500 opacity-50 cursor-not-allowed"
          >
            Revise draft
          </button>
          <button
            type="button"
            disabled
            class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-500 opacity-50 cursor-not-allowed"
          >
            Polish draft
          </button>
          <button
            type="button"
            disabled
            class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-500 opacity-50 cursor-not-allowed"
          >
            Clarify bullets
          </button>
        </div>
      </article>
    </div>

    <aside class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <p class="text-sm font-medium text-slate-500">Navigation</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          Return to the drafts list or browse applications. The legacy draft UI remains available if you need preview edits or clarification tools.
        </p>
      </div>

        <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <p class="text-sm font-medium text-slate-500">Related workflow</p>
        <div v-if="linkedJob" class="mt-3 rounded-lg border border-slate-200 bg-white p-3">
          <p class="text-xs font-semibold uppercase text-slate-500">Linked job</p>
          <p class="mt-2 text-sm font-medium text-slate-950">{{ linkedJob.title || detailLabel }}</p>
          <p v-if="linkedJob.company || linkedJob.location" class="mt-1 text-xs text-slate-500">
            {{ linkedJob.company || detailCompany }}
            <span v-if="linkedJob.company && linkedJob.location"> · </span>
            <span v-if="linkedJob.location">{{ linkedJob.location }}</span>
          </p>
        </div>
        <div class="mt-3 rounded-lg border border-slate-200 bg-white p-3">
          <p class="text-xs font-semibold uppercase text-slate-500">Application tracking</p>
          <p class="mt-2 text-sm text-slate-600">
            Jump back to the draft queue, browse jobs, or review tracked applications.
          </p>
          <p v-if="linkedApplicationId" class="mt-2 text-xs text-slate-500">
            Linked application {{ linkedApplicationId.slice(0, 8) }}<span v-if="linkedApplicationStatus"> · {{ linkedApplicationStatus }}</span>
          </p>
        </div>
        <div class="mt-4 space-y-3">
          <RouterLink
            to="/drafts"
            class="block rounded-xl bg-slate-950 px-4 py-2 text-center text-sm font-medium text-white hover:bg-slate-800"
          >
            Back to drafts
          </RouterLink>
          <RouterLink
            :to="linkedJobTarget"
            class="block rounded-xl border border-slate-200 bg-white px-4 py-2 text-center text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {{ linkedJobLinkLabel }}
          </RouterLink>
          <RouterLink
            :to="linkedApplicationTarget"
            class="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-center text-sm font-medium text-slate-900 hover:bg-slate-100"
          >
            {{ linkedApplicationLinkLabel }}
          </RouterLink>
        </div>
      </div>

      <dl class="space-y-3 text-sm">
        <div class="flex items-start justify-between gap-4">
          <dt class="text-slate-500">Loading</dt>
          <dd class="font-medium text-slate-950">{{ loading ? "Yes" : "No" }}</dd>
        </div>
        <div class="flex items-start justify-between gap-4">
          <dt class="text-slate-500">Action busy</dt>
          <dd class="font-medium text-slate-950">{{ actionLoading ? "Yes" : "No" }}</dd>
        </div>
        <div class="flex items-start justify-between gap-4">
          <dt class="text-slate-500">Cover letter loaded</dt>
          <dd class="font-medium text-slate-950">{{ coverLetter ? "Yes" : "No" }}</dd>
        </div>
        <div class="flex items-start justify-between gap-4">
          <dt class="text-slate-500">Draft ID</dt>
          <dd class="font-mono text-xs text-slate-950 break-all">{{ draftId || "None" }}</dd>
        </div>
      </dl>

      <div class="space-y-3">
        <a
          :href="`/ui/drafts/${draftId}`"
          class="block rounded-xl border border-slate-200 bg-white px-4 py-2 text-center text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Legacy draft detail
        </a>
      </div>
    </aside>
  </section>
</template>
