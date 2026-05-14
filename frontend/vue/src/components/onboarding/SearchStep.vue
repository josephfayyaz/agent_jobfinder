<script setup>
import StatusMessage from "./StatusMessage.vue";

defineProps({
  search: { type: Object, required: true },
});

const emit = defineEmits(["back"]);
</script>

<template>
  <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
    <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Search</p>
        <h2 class="mt-1 text-2xl font-semibold text-slate-950">Choose your search focus</h2>
        <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Keep this short. The app uses these choices to guide discovery, ranking, and language
          filtering.
        </p>
      </div>
    </div>

    <div class="mt-6 space-y-5">
      <label class="block">
        <span class="text-sm font-medium text-slate-700">Target roles, one per line</span>
        <textarea
          v-model="search.searchRolesText.value"
          class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          rows="5"
          placeholder="Enter only the roles you actually want"
          :disabled="search.searchSaving.value"
          @input="search.markSearchRolesTouched"
        ></textarea>
        <p class="mt-1 text-xs text-slate-500">
          Choose up to 4 roles. You can keep one, pick a few suggestions, or type your own.
        </p>
      </label>

      <div
        v-if="search.suggestedRoles.value.length || search.suggestionsBusy.value"
        class="rounded-lg border border-indigo-100 bg-indigo-50 px-4 py-3"
      >
        <div class="flex items-center justify-between gap-2">
          <p class="text-xs font-semibold uppercase tracking-wide text-indigo-700">
            Detected role suggestions
          </p>
          <span class="text-xs text-slate-500">
            {{ search.suggestionsBusy.value ? "Refining with AI..." : "" }}
          </span>
        </div>
        <div class="mt-2 flex flex-wrap gap-2">
          <template v-if="search.suggestionsBusy.value && !search.suggestedRoles.value.length">
            <span class="h-7 w-24 animate-pulse rounded-full bg-indigo-100"></span>
            <span class="h-7 w-32 animate-pulse rounded-full bg-indigo-100"></span>
            <span class="h-7 w-28 animate-pulse rounded-full bg-indigo-100"></span>
          </template>
          <button
            v-for="role in search.suggestedRoles.value"
            :key="role"
            type="button"
            class="rounded-full border border-indigo-200 bg-white px-3 py-1 text-sm font-medium text-indigo-700 transition hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="search.searchSaving.value"
            @click="search.addSuggestedRole(role)"
          >
            {{ role }}
          </button>
        </div>
      </div>

      <div class="grid gap-4 md:grid-cols-2">
        <label class="block">
          <span class="text-sm font-medium text-slate-700">Target country</span>
          <textarea
            v-model="search.searchCountry.value"
            class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            rows="2"
            :disabled="search.searchSaving.value"
            @input="search.markSearchCountryTouched"
          ></textarea>
          <p class="mt-1 text-xs text-slate-500">This release supports one country. Default: Italy.</p>
        </label>

        <label class="block">
          <span class="text-sm font-medium text-slate-700">Seniority</span>
          <select
            v-model="search.searchSeniority.value"
            class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            :disabled="search.searchSaving.value"
          >
            <option value="intern">intern</option>
            <option value="junior">junior</option>
            <option value="mid">mid</option>
            <option value="senior">senior</option>
            <option value="any">any</option>
          </select>
        </label>
      </div>

      <section class="rounded-lg border border-slate-200 bg-slate-50 px-4 py-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="text-sm font-semibold text-slate-900">Job description languages</p>
            <p class="mt-1 text-sm text-slate-500">
              Confirm the languages you can read for job descriptions and set your proficiency.
            </p>
          </div>
          <button
            type="button"
            class="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="search.searchSaving.value"
            @click="search.addSearchLanguage"
          >
            Add language
          </button>
        </div>

        <div class="mt-4 space-y-3">
          <div
            v-for="(row, index) in search.searchLanguages.value"
            :key="`search-language-${index}`"
            class="grid gap-3 rounded-md border border-slate-200 bg-white p-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]"
          >
            <label class="block">
              <span class="text-sm font-medium text-slate-700">Language</span>
              <select
                v-model="row.name"
                class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                :disabled="search.searchSaving.value"
                @change="search.markSearchLanguagesTouched"
              >
                <option
                  v-for="option in search.searchLanguageOptions.value"
                  :key="search.languageOptionValue(option)"
                  :value="search.languageOptionValue(option)"
                >
                  {{ search.languageOptionLabel(option) }}
                </option>
              </select>
            </label>
            <label class="block">
              <span class="text-sm font-medium text-slate-700">Level</span>
              <select
                v-model="row.level"
                class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                :disabled="search.searchSaving.value"
                @change="search.markSearchLanguagesTouched"
              >
                <option
                  v-for="option in search.searchLevelOptions.value"
                  :key="search.levelOptionValue(option)"
                  :value="search.levelOptionValue(option)"
                >
                  {{ search.levelOptionLabel(option) }}
                </option>
              </select>
            </label>
            <button
              type="button"
              class="self-end rounded-md border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="search.searchSaving.value"
              @click="search.removeSearchLanguage(index)"
            >
              Remove
            </button>
          </div>
        </div>
      </section>

      <section class="rounded-lg border border-slate-200 bg-white px-4 py-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="text-sm font-semibold text-slate-900">Discovery hints</p>
            <p class="mt-1 text-sm text-slate-500">
              Job Agent will prioritise likely job channels from your roles and countries. You can refine sources later in Settings.
            </p>
          </div>
          <a href="/ui/settings#discovery-form" class="text-xs font-semibold text-indigo-700 underline">
            Edit later
          </a>
        </div>
        <div class="mt-3 flex flex-wrap gap-2 text-sm text-slate-600">
          <p v-if="search.searchBusy.value" class="text-slate-400">Loading suggestions...</p>
          <p v-else-if="!search.recommendedSources.value.length" class="text-slate-400">
            Suggestions will appear after your profile is analysed.
          </p>
          <template v-else>
            <span
              v-for="source in search.recommendedSources.value"
              :key="source.slug || source.name"
              class="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-700"
              :title="source.why || ''"
            >
              {{ source.name }}
            </span>
          </template>
        </div>
      </section>

      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <StatusMessage
          :message="search.searchStatus.value"
          :is-error="search.searchStatusError.value"
        />
        <div class="flex gap-3">
          <button
            type="button"
            class="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="search.searchSaving.value"
            @click="emit('back')"
          >
            Back
          </button>
          <button
            type="button"
            class="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            :disabled="search.searchSaving.value"
            @click="search.saveSearchFocus"
          >
            {{ search.searchSaving.value ? "Saving..." : "Finish setup" }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
