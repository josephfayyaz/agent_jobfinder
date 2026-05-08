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
    payload.value = await vueApiFetch("/companies");
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

const companyLabel = (item) => item?.company || item?.name || "Unnamed company";
const companyId = (item) => item?.id || "";
const companyStatus = (item) => {
  if (typeof item?.active === "boolean") {
    return item.active ? "Active" : "Inactive";
  }

  return item?.status || item?.source || "Unknown status";
};
const companyLocation = (item) => item?.country || item?.location || "Location not provided";
const companyUrl = (item) => item?.career_url || "";
</script>

<template>
  <AppPageHeader
    title="Companies"
    description="A read-only view of tracked company sources and their current research status."
  />

  <section class="grid gap-12 lg:grid-cols-12">
    <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-full">
      <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        Tracked companies
      </h2>

      <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        Loading companies...
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
          The backend is still returning placeholder companies data, so the list below is rendered safely from whatever is available.
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
            :key="companyId(item) || companyLabel(item)"
            class="rounded-xl border border-slate-200 bg-white p-4"
          >
            <div class="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
              <div>
                <h3 class="text-sm font-semibold text-slate-950">{{ companyLabel(item) }}</h3>
                <p class="mt-1 text-sm text-slate-600">{{ companyLocation(item) }}</p>
              </div>
              <p class="text-sm font-medium text-slate-900">{{ companyStatus(item) }}</p>
            </div>

            <dl class="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-2">
              <div>
                <dt class="text-slate-500">ID</dt>
                <dd class="mt-1 font-mono text-slate-950">{{ companyId(item) || "Not provided" }}</dd>
              </div>
              <div>
                <dt class="text-slate-500">Career URL</dt>
                <dd class="mt-1 break-all text-slate-950">
                  <a
                    v-if="companyUrl(item)"
                    :href="companyUrl(item)"
                    target="_blank"
                    rel="noreferrer"
                    class="font-medium text-slate-950 underline decoration-slate-300 underline-offset-2"
                  >
                    {{ companyUrl(item) }}
                  </a>
                  <span v-else>Not provided</span>
                </dd>
              </div>
            </dl>
          </article>
        </div>

        <div
          v-else
          class="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600"
        >
          No companies are currently available in the contract response.
        </div>
      </div>
    </article>
  </section>
</template>
