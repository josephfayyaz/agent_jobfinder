<script setup>
import LanguageRowsEditor from "./LanguageRowsEditor.vue";
import SettingsStatusMessage from "./SettingsStatusMessage.vue";

const seniorityOptions = ["intern", "junior", "mid", "senior", "any"];

const props = defineProps({
  search: {
    type: Object,
    required: true,
  },
  roleCount: {
    type: Number,
    required: true,
  },
  roleLimitExceeded: {
    type: Boolean,
    required: true,
  },
  languageOptions: {
    type: Array,
    default: () => [],
  },
  languageLevelOptions: {
    type: Array,
    default: () => [],
  },
  status: {
    type: Object,
    required: true,
  },
  saving: {
    type: Boolean,
    default: false,
  },
  suggestionsLoading: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits([
  "update:field",
  "add-language",
  "remove-language",
  "update-language",
  "refresh-suggestions",
  "save-search",
]);

function update(field, event) {
  emit("update:field", field, event.target.type === "checkbox" ? event.target.checked : event.target.value);
}
</script>

<template>
  <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
    <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Search preferences</p>
        <h2 class="mt-1 text-xl font-semibold text-slate-950">Job discovery scope</h2>
      </div>
      <button
        type="button"
        class="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
        :disabled="suggestionsLoading"
        @click="emit('refresh-suggestions')"
      >
        {{ suggestionsLoading ? "Refreshing..." : "Refresh role suggestions" }}
      </button>
    </div>

    <div class="mt-5 space-y-5">
      <div>
        <span class="text-sm font-medium text-slate-700">Target seniority</span>
        <div class="mt-2 grid gap-2 sm:grid-cols-5">
          <label v-for="level in seniorityOptions" :key="level" class="cursor-pointer">
            <input
              class="sr-only"
              type="radio"
              name="targetSeniority"
              :value="level"
              :checked="props.search.targetSeniority === level"
              @change="update('targetSeniority', $event)"
            />
            <span
              :class="[
                'block rounded-md border px-3 py-2 text-center text-sm font-semibold capitalize',
                props.search.targetSeniority === level
                  ? 'border-sky-500 bg-sky-50 text-sky-800'
                  : 'border-slate-200 bg-white text-slate-600'
              ]"
            >
              {{ level }}
            </span>
          </label>
        </div>
      </div>

      <div class="grid gap-4 md:grid-cols-3">
        <label class="block">
          <span class="text-sm font-medium text-slate-700">Match minimum score</span>
          <input
            :value="props.search.matchMinScore"
            type="number"
            min="0"
            max="100"
            class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            @input="update('matchMinScore', $event)"
          />
        </label>
        <label class="block">
          <span class="text-sm font-medium text-slate-700">Default fit threshold</span>
          <input
            :value="props.search.discoveryMinFitScore"
            type="number"
            min="40"
            max="100"
            class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            @input="update('discoveryMinFitScore', $event)"
          />
        </label>
        <label class="block">
          <span class="text-sm font-medium text-slate-700">Visible queue cap</span>
          <input
            :value="props.search.discoveryMaxVisibleJobs"
            type="number"
            min="20"
            max="200"
            class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            @input="update('discoveryMaxVisibleJobs', $event)"
          />
        </label>
      </div>

      <div class="grid gap-4 md:grid-cols-2">
        <label class="block">
          <span class="text-sm font-medium text-slate-700">Target country</span>
          <textarea
            :value="props.search.countriesText"
            rows="2"
            class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            @input="update('countriesText', $event)"
          />
          <span class="mt-1 block text-xs text-slate-500">Only the first country is saved. Empty defaults to Italy.</span>
        </label>
        <label class="block">
          <span class="text-sm font-medium text-slate-700">Primary discovery location</span>
          <input
            :value="props.search.jobspyDiscoverLocation"
            type="text"
            class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            @input="update('jobspyDiscoverLocation', $event)"
          />
        </label>
      </div>

      <label class="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
        <span>
          <span class="block text-sm font-medium text-slate-700">Automatic JobSpy</span>
          <span class="mt-1 block text-xs text-slate-500">Use saved search preferences for automated discovery.</span>
        </span>
        <input
          :checked="props.search.useJobspy"
          type="checkbox"
          class="h-5 w-5 rounded border-slate-300 text-sky-700 focus:ring-sky-500"
          @change="update('useJobspy', $event)"
        />
      </label>

      <label class="block">
        <div class="flex items-center justify-between gap-3">
          <span class="text-sm font-medium text-slate-700">Target roles</span>
          <span
            :class="[
              'rounded-md px-2 py-1 text-xs font-semibold',
              roleLimitExceeded ? 'bg-rose-50 text-rose-700' : 'bg-slate-100 text-slate-600'
            ]"
          >
            {{ roleCount }}/4 roles
          </span>
        </div>
        <textarea
          :value="props.search.rolesText"
          rows="5"
          class="mt-1 w-full rounded-md border bg-white px-3 py-2 font-mono text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          :class="roleLimitExceeded ? 'border-rose-300' : 'border-slate-300'"
          @input="update('rolesText', $event)"
        />
        <span v-if="roleLimitExceeded" class="mt-1 block text-xs font-medium text-rose-700">
          More than 4 roles can make search quality worse and may be rejected by the backend.
        </span>
      </label>

      <LanguageRowsEditor
        :rows="props.search.languages"
        :language-options="languageOptions"
        :level-options="languageLevelOptions"
        @add-language="emit('add-language')"
        @remove-language="(index) => emit('remove-language', index)"
        @update-language="(index, field, value) => emit('update-language', index, field, value)"
      />

      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SettingsStatusMessage :message="status.message" :tone="status.tone" />
        <button
          type="button"
          class="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          :disabled="saving"
          @click="emit('save-search')"
        >
          {{ saving ? "Saving..." : "Save Search Settings" }}
        </button>
      </div>
    </div>
  </section>
</template>
