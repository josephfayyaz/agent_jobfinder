<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";
import { vueApiFetch } from "../api/client";

const loading = ref(true);
const error = ref("");
const payload = ref(null);

onMounted(async () => {
  try {
    payload.value = await vueApiFetch("/applications");
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
const items = computed(() => (Array.isArray(responseData.value.items) ? responseData.value.items.filter(Boolean) : []));
const total = computed(() => responseData.value.total ?? items.value.length ?? 0);

const appLabel = (item) => item?.title || item?.role || (item?.id ? `Application ${String(item.id).slice(0, 8)}` : null) || "Untitled application";
const appCompany = (item) => item?.company || "Unknown company";
const appStatus = (item) => item?.status || "Status unavailable";
const appId = (item) => item?.id || "";
const appNextAction = (item) => item?.next_action || "";
const appAppliedAt = (item) => item?.applied_at || item?.created_at || "";
const appDraftId = (item) => item?.resume_draft_id || "";
const appJobId = (item) => item?.job_id || item?.job_post_id || "";
</script>

<template>
  <AppPageHeader
    title="Applications"
    description="A read-only view of tracked applications and their current status."
  />

  <section class="grid gap-12 lg:grid-cols-12">
    <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-full">
      <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        Tracked applications
      </h2>

      <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        Loading applications...
      </div>

      <div v-else-if="error" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
        {{ error }}
      </div>

      <div v-else class="mt-4 space-y-4">
        <p class="text-sm leading-6 text-slate-600">
          {{ responseMessage || "" }}
        </p>

        <div
          v-if="isPlaceholder"
          class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
        >
          The backend is still returning placeholder applications data, so the list below is rendered safely from whatever is available.
        </div>

        <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <p class="text-sm font-medium text-slate-500">Total</p>
            <p class="text-lg font-semibold text-slate-950">{{ total }}</p>
          </div>
        </div>

        <div v-if="items.length" class="space-y-3">
          <article
            v-for="item in items"
            :key="appId(item) || appLabel(item)"
            class="rounded-xl border border-slate-200 bg-white p-4"
          >
            <div class="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
              <div>
                <h3 class="text-sm font-semibold text-slate-950">
                  <RouterLink
                    v-if="appId(item)"
                    :to="`/applications/${appId(item)}`"
                    class="hover:underline"
                  >
                    {{ appLabel(item) }}
                  </RouterLink>
                  <span v-else>{{ appLabel(item) }}</span>
                </h3>
                <p class="mt-1 text-sm text-slate-600">{{ appCompany(item) }}</p>
              </div>
              <p class="text-sm font-medium text-slate-900">{{ appStatus(item) }}</p>
            </div>

            <dl class="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-2">
              <div>
                <dt class="text-slate-500">ID</dt>
                <dd class="mt-1 font-mono text-slate-950">{{ appId(item) || "Not provided" }}</dd>
              </div>
              <div v-if="appNextAction(item)">
                <dt class="text-slate-500">Next action</dt>
                <dd class="mt-1 text-slate-950">{{ appNextAction(item) }}</dd>
              </div>
              <div v-if="appAppliedAt(item)">
                <dt class="text-slate-500">Applied</dt>
                <dd class="mt-1 text-slate-950">{{ appAppliedAt(item) }}</dd>
              </div>
              <div v-if="appDraftId(item)">
                <dt class="text-slate-500">Draft</dt>
                <dd class="mt-1 font-mono text-slate-950">
                  <RouterLink
                    :to="`/drafts/${appDraftId(item)}`"
                    class="underline decoration-slate-300 underline-offset-2 hover:text-slate-950"
                  >
                    {{ String(appDraftId(item)).slice(0, 8) }}
                  </RouterLink>
                </dd>
              </div>
            </dl>

            <div class="mt-4 flex flex-wrap gap-3">
              <RouterLink
                v-if="appId(item)"
                :to="`/applications/${appId(item)}`"
                class="inline-block rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100"
              >
                View application detail
              </RouterLink>
              <RouterLink
                v-if="appJobId(item)"
                :to="`/jobs/${appJobId(item)}`"
                class="inline-block rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                View linked job
              </RouterLink>
            </div>
          </article>
        </div>

        <div
          v-else
          class="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600"
        >
          No applications are currently available in the contract response.
        </div>
      </div>
    </article>
  </section>
</template>
