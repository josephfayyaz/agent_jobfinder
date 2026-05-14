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
    payload.value = await vueApiFetch("/thesis/targets");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});

const responseData = computed(() => payload.value?.data ?? {});
const items = computed(() => (Array.isArray(responseData.value.items) ? responseData.value.items.filter(Boolean) : []));
const total = computed(() => responseData.value.total ?? items.value.length ?? 0);

const targetName = (item) => item?.name || "Unnamed target";
const targetInstitution = (item) => item?.institution || "";
const targetCountry = (item) => item?.country || "";
const targetType = (item) => item?.type || "";
const targetStatus = (item) => item?.status || "Status unavailable";
const targetPriority = (item) => (typeof item?.priority === "number" ? item.priority : null);
const targetId = (item) => item?.id || "";
const targetUpdatedAt = (item) => item?.updated_at || "";

const typeBadgeClass = (type) => {
  if (type === "professor") return "border-indigo-200 bg-indigo-50 text-indigo-800";
  if (type === "lab") return "border-violet-200 bg-violet-50 text-violet-800";
  if (type === "company") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  return "border-slate-200 bg-slate-50 text-slate-700";
};
</script>

<template>
  <AppPageHeader
    title="Thesis"
    description="A read-only view of thesis and traineeship targets with outreach status."
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
      <p class="text-sm font-medium text-slate-500">Thesis target tracking</p>
      <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        Tracked targets
      </h2>

      <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        Loading thesis targets...
      </div>

      <div v-else-if="error" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
        {{ error }}
      </div>

      <div v-else class="mt-4 space-y-4">
        <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <p class="text-sm font-medium text-slate-500">Total</p>
            <p class="text-lg font-semibold text-slate-950">{{ total }}</p>
          </div>
        </div>

        <div v-if="items.length" class="space-y-3">
          <article
            v-for="item in items"
            :key="targetId(item) || targetName(item)"
            class="rounded-xl border border-slate-200 bg-white p-4"
          >
            <div class="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
              <div>
                <div class="flex flex-wrap items-center gap-2">
                  <h3 class="text-sm font-semibold text-slate-950">{{ targetName(item) }}</h3>
                  <span
                    v-if="targetType(item)"
                    :class="['inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium', typeBadgeClass(targetType(item))]"
                  >
                    {{ targetType(item) }}
                  </span>
                </div>
                <p v-if="targetInstitution(item)" class="mt-1 text-sm text-slate-600">{{ targetInstitution(item) }}</p>
              </div>
              <div class="flex items-center gap-2">
                <span
                  v-if="targetPriority(item) !== null"
                  class="inline-flex items-center rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-600"
                >
                  P{{ targetPriority(item) }}
                </span>
                <p class="text-sm font-medium text-slate-900">{{ targetStatus(item) }}</p>
              </div>
            </div>

            <dl class="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-2">
              <div v-if="targetCountry(item)">
                <dt class="text-slate-500">Country</dt>
                <dd class="mt-1 text-slate-950">{{ targetCountry(item) }}</dd>
              </div>
              <div v-if="targetUpdatedAt(item)">
                <dt class="text-slate-500">Updated</dt>
                <dd class="mt-1 text-slate-950">{{ targetUpdatedAt(item) }}</dd>
              </div>
              <div v-if="targetId(item)">
                <dt class="text-slate-500">ID</dt>
                <dd class="mt-1 font-mono text-xs text-slate-950 break-all">{{ targetId(item) }}</dd>
              </div>
            </dl>
          </article>
        </div>

        <div
          v-else
          class="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600"
        >
          No thesis targets are currently tracked. Add targets through the legacy thesis interface to see them here.
        </div>
      </div>
    </article>

    <aside class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <p class="text-sm font-medium text-slate-500">Next actions</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          Thesis targets track professors, labs, and companies for outreach. Review job opportunities or companies for additional sourcing.
        </p>
      </div>

      <dl class="space-y-3 text-sm">
        <div class="flex items-start justify-between gap-4">
          <dt class="text-slate-500">Loading</dt>
          <dd class="font-medium text-slate-950">{{ loading ? "Yes" : "No" }}</dd>
        </div>
        <div class="flex items-start justify-between gap-4">
          <dt class="text-slate-500">Error</dt>
          <dd class="font-medium text-slate-950">{{ error ? "Present" : "None" }}</dd>
        </div>
        <div class="flex items-start justify-between gap-4">
          <dt class="text-slate-500">Total targets</dt>
          <dd class="font-medium text-slate-950">{{ total }}</dd>
        </div>
      </dl>

      <div class="space-y-3">
        <RouterLink
          to="/applications"
          class="block rounded-xl bg-slate-950 px-4 py-2 text-center text-sm font-medium text-white hover:bg-slate-800"
        >
          Go to Applications
        </RouterLink>
        <RouterLink
          to="/jobs"
          class="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-center text-sm font-medium text-slate-900 hover:bg-slate-100"
        >
          Go to Jobs
        </RouterLink>
        <RouterLink
          to="/companies"
          class="block rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-center text-sm font-medium text-emerald-900 hover:bg-emerald-100"
        >
          Go to Companies
        </RouterLink>
      </div>
    </aside>
  </section>
</template>
