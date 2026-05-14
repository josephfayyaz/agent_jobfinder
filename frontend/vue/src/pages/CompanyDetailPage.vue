<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";
import { vueApiFetch } from "../api/client";

const route = useRoute();
const companyId = computed(() => String(route.params.id || ""));

const loading = ref(true);
const error = ref("");
const payload = ref(null);

onMounted(async () => {
  if (!companyId.value) {
    error.value = "No company ID provided in route.";
    loading.value = false;
    return;
  }

  try {
    payload.value = await vueApiFetch(`/companies/${companyId.value}`);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});

const detail = computed(() => payload.value?.data?.item ?? {});
const detailName = computed(() => detail.value?.company || detail.value?.name || "Unnamed company");
const detailStatus = computed(() => {
  if (typeof detail.value?.active === "boolean") {
    return detail.value.active ? "Active" : "Inactive";
  }
  return detail.value?.status || "Unknown status";
});
const detailLocation = computed(() => detail.value?.country || detail.value?.location || "");
const detailLastChecked = computed(() => detail.value?.last_checked_at || "");
const detailLastNewJobs = computed(() => detail.value?.last_new_jobs ?? null);
const careerPageStored = computed(() => detail.value?.career_page_url_available === true);
</script>

<template>
  <AppPageHeader
    title="Company Detail"
    :description="`Review tracked company context for ${companyId || '(unknown)'}.`"
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <div class="space-y-6 lg:col-span-2">
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Company detail</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{{ detailName }}</h2>

        <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Loading company...
        </div>

        <div v-else-if="error" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          {{ error }}
        </div>

        <dl v-else class="mt-4 grid gap-4 text-sm md:grid-cols-2">
          <div>
            <dt class="text-slate-500">Status</dt>
            <dd class="mt-1 font-medium text-slate-950">{{ detailStatus }}</dd>
          </div>
          <div>
            <dt class="text-slate-500">Company ID</dt>
            <dd class="mt-1 font-mono text-xs text-slate-950 break-all">{{ companyId || "Not provided" }}</dd>
          </div>
          <div v-if="detailLocation">
            <dt class="text-slate-500">Location</dt>
            <dd class="mt-1 text-slate-950">{{ detailLocation }}</dd>
          </div>
          <div>
            <dt class="text-slate-500">Career page stored</dt>
            <dd class="mt-1 text-slate-950">{{ careerPageStored ? "Yes" : "No" }}</dd>
          </div>
        </dl>
      </article>

      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Career source status</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">Tracking overview</h2>

        <div class="mt-4 grid gap-4 text-sm md:grid-cols-2">
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-semibold uppercase text-slate-500">Last checked</p>
            <p class="mt-2 text-sm font-medium text-slate-950">{{ detailLastChecked || "Not checked yet" }}</p>
          </div>

          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-semibold uppercase text-slate-500">New jobs detected</p>
            <p class="mt-2 text-sm font-medium text-slate-950">{{ detailLastNewJobs ?? 0 }}</p>
          </div>
        </div>
      </article>
    </div>

    <aside class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <p class="text-sm font-medium text-slate-500">Related workflow</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          Use the company context here as a starting point, then jump back to jobs or applications for the broader workflow.
        </p>
      </div>

      <div class="space-y-3">
        <RouterLink
          to="/companies"
          class="block rounded-xl bg-slate-950 px-4 py-2 text-center text-sm font-medium text-white hover:bg-slate-800"
        >
          Back to companies
        </RouterLink>
        <RouterLink
          to="/jobs"
          class="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-center text-sm font-medium text-slate-900 hover:bg-slate-100"
        >
          View jobs
        </RouterLink>
        <RouterLink
          to="/applications"
          class="block rounded-xl border border-slate-200 bg-white px-4 py-2 text-center text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          View applications
        </RouterLink>
      </div>
    </aside>
  </section>
</template>
