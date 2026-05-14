<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";
import { vueApiFetch } from "../api/client";

const route = useRoute();
const applicationId = computed(() => String(route.params.id || ""));

const loading = ref(true);
const error = ref("");
const payload = ref(null);

onMounted(async () => {
  if (!applicationId.value) {
    error.value = "No application ID provided in route.";
    loading.value = false;
    return;
  }

  try {
    payload.value = await vueApiFetch(`/applications/${applicationId.value}`);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});

const detail = computed(() => payload.value?.data?.item ?? {});
const linkedJob = computed(() => detail.value?.job ?? null);
const linkedDraft = computed(() => detail.value?.draft ?? null);

const detailLabel = computed(() => (
  detail.value?.title
  || linkedJob.value?.title
  || (applicationId.value ? `Application ${applicationId.value.slice(0, 8)}` : "Untitled application")
));
const detailCompany = computed(() => detail.value?.company || linkedJob.value?.company || "Unknown company");
const detailLocation = computed(() => detail.value?.location || linkedJob.value?.location || "");
const detailStatus = computed(() => detail.value?.status || "Status unavailable");
const detailAppliedAt = computed(() => detail.value?.applied_at || detail.value?.created_at || "");
const detailUpdatedAt = computed(() => detail.value?.updated_at || "");
const detailNextAction = computed(() => detail.value?.next_action || "");
const linkedJobTarget = computed(() => (
  detail.value?.job_id ? `/jobs/${detail.value.job_id}` : "/jobs"
));
const linkedDraftTarget = computed(() => (
  detail.value?.draft_id ? `/drafts/${detail.value.draft_id}` : "/drafts"
));
const linkedJobLabel = computed(() => (
  detail.value?.job_id ? "View linked job" : "View jobs"
));
const linkedDraftLabel = computed(() => (
  detail.value?.draft_id ? "View linked draft" : "View drafts"
));
</script>

<template>
  <AppPageHeader
    title="Application Detail"
    :description="`Review application context for ${applicationId || '(unknown)'}.`"
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <div class="space-y-6 lg:col-span-2">
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Application detail</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{{ detailLabel }}</h2>

        <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Loading application...
        </div>

        <div v-else-if="error" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          {{ error }}
        </div>

        <dl v-else class="mt-4 grid gap-4 text-sm md:grid-cols-2">
          <div>
            <dt class="text-slate-500">Company</dt>
            <dd class="mt-1 text-slate-950">{{ detailCompany }}</dd>
          </div>
          <div>
            <dt class="text-slate-500">Status</dt>
            <dd class="mt-1 font-medium text-slate-950">{{ detailStatus }}</dd>
          </div>
          <div v-if="detailLocation">
            <dt class="text-slate-500">Location</dt>
            <dd class="mt-1 text-slate-950">{{ detailLocation }}</dd>
          </div>
          <div>
            <dt class="text-slate-500">Application ID</dt>
            <dd class="mt-1 font-mono text-xs text-slate-950 break-all">{{ applicationId || "Not provided" }}</dd>
          </div>
          <div v-if="detailNextAction">
            <dt class="text-slate-500">Next action</dt>
            <dd class="mt-1 text-slate-950">{{ detailNextAction }}</dd>
          </div>
          <div v-if="detailAppliedAt">
            <dt class="text-slate-500">Applied</dt>
            <dd class="mt-1 text-slate-950">{{ detailAppliedAt }}</dd>
          </div>
          <div v-if="detailUpdatedAt">
            <dt class="text-slate-500">Updated</dt>
            <dd class="mt-1 text-slate-950">{{ detailUpdatedAt }}</dd>
          </div>
        </dl>
      </article>

      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Linked job</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">Job context</h2>

        <div v-if="linkedJob" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
          <p class="text-sm font-medium text-slate-950">{{ linkedJob.title || detailLabel }}</p>
          <p class="mt-1 text-sm text-slate-600">{{ linkedJob.company || detailCompany }}</p>
          <p v-if="linkedJob.location" class="mt-1 text-xs text-slate-500">{{ linkedJob.location }}</p>
          <p v-if="linkedJob.status" class="mt-3 text-xs font-medium uppercase text-slate-500">
            {{ linkedJob.status }}
          </p>
        </div>

        <div v-else class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          No linked job metadata is available for this application yet.
        </div>
      </article>

      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Status</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">Application tracking</h2>

        <div class="mt-4 grid gap-4 text-sm md:grid-cols-2">
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-semibold uppercase text-slate-500">Current status</p>
            <p class="mt-2 text-sm font-medium text-slate-950">{{ detailStatus }}</p>
          </div>

          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-semibold uppercase text-slate-500">Linked draft</p>
            <p class="mt-2 text-sm font-medium text-slate-950">
              {{ linkedDraft?.title || (detail.draft_id ? `Draft ${String(detail.draft_id).slice(0, 8)}` : "Not linked") }}
            </p>
            <p v-if="linkedDraft?.status" class="mt-1 text-xs text-slate-500">
              {{ linkedDraft.status }}<span v-if="typeof linkedDraft?.approved === 'boolean'"> · Approved {{ linkedDraft.approved ? "Yes" : "No" }}</span>
            </p>
          </div>
        </div>
      </article>
    </div>

    <aside class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <p class="text-sm font-medium text-slate-500">Related workflow</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          Jump between the application queue, linked job context, and the related draft without changing any status from this page.
        </p>
      </div>

      <div class="space-y-3">
        <RouterLink
          to="/applications"
          class="block rounded-xl bg-slate-950 px-4 py-2 text-center text-sm font-medium text-white hover:bg-slate-800"
        >
          Back to applications
        </RouterLink>
        <RouterLink
          :to="linkedJobTarget"
          class="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-center text-sm font-medium text-slate-900 hover:bg-slate-100"
        >
          {{ linkedJobLabel }}
        </RouterLink>
        <RouterLink
          :to="linkedDraftTarget"
          class="block rounded-xl border border-slate-200 bg-white px-4 py-2 text-center text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          {{ linkedDraftLabel }}
        </RouterLink>
        <RouterLink
          to="/jobs"
          class="block rounded-xl border border-slate-200 bg-white px-4 py-2 text-center text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          View jobs
        </RouterLink>
        <RouterLink
          to="/drafts"
          class="block rounded-xl border border-slate-200 bg-white px-4 py-2 text-center text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          View drafts
        </RouterLink>
      </div>
    </aside>
  </section>
</template>
