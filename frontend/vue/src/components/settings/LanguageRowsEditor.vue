<script setup>
defineProps({
  rows: {
    type: Array,
    required: true,
  },
  languageOptions: {
    type: Array,
    default: () => [],
  },
  levelOptions: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["add-language", "remove-language", "update-language"]);

function update(index, field, event) {
  emit("update-language", index, field, event.target.value);
}
</script>

<template>
  <section class="rounded-lg border border-slate-200 bg-slate-50 p-4">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h3 class="text-sm font-semibold text-slate-950">Job description languages</h3>
        <p class="mt-1 text-sm leading-6 text-slate-600">Choose the languages you can realistically read.</p>
      </div>
      <button
        type="button"
        class="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
        @click="emit('add-language')"
      >
        Add language
      </button>
    </div>

    <div class="mt-4 space-y-3">
      <div
        v-for="(row, index) in rows"
        :key="`${row.name}-${index}`"
        class="grid gap-3 rounded-lg border border-slate-200 bg-white p-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]"
      >
        <label class="block">
          <span class="text-xs font-semibold uppercase tracking-wide text-slate-500">Language</span>
          <select
            :value="row.name"
            class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            @change="update(index, 'name', $event)"
          >
            <option
              v-for="option in languageOptions"
              :key="option.code || option.name"
              :value="option.name"
            >
              {{ option.name }}
            </option>
          </select>
        </label>

        <label class="block">
          <span class="text-xs font-semibold uppercase tracking-wide text-slate-500">Level</span>
          <select
            :value="row.level"
            class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            @change="update(index, 'level', $event)"
          >
            <option
              v-for="option in levelOptions"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </label>

        <button
          type="button"
          class="self-end rounded-md border border-rose-200 bg-white px-3 py-2 text-sm font-semibold text-rose-700 shadow-sm hover:bg-rose-50"
          @click="emit('remove-language', index)"
        >
          Remove
        </button>
      </div>
    </div>
  </section>
</template>
