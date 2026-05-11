<script setup>
const props = defineProps({
  mode: {
    type: String,
    required: true,
  },
  modelValue: {
    type: Object,
    required: true,
  },
  lmStudioModels: {
    type: Array,
    default: () => [],
  },
  ollamaModels: {
    type: Array,
    default: () => [],
  },
  lmStudioLoading: {
    type: Boolean,
    default: false,
  },
  ollamaLoading: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update:field", "test-lm-studio", "test-ollama"]);

function update(field, event) {
  emit("update:field", field, event.target.value);
}
</script>

<template>
  <section
    v-if="['lm_studio', 'ollama'].includes(mode)"
    class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
  >
    <div class="mb-5">
      <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Local provider</p>
      <h2 class="mt-1 text-xl font-semibold text-slate-950">Local model settings</h2>
      <p class="mt-1 max-w-2xl text-sm leading-6 text-slate-600">
        One selected chat model is reused for intake, drafting, and review.
      </p>
    </div>

    <div v-if="mode === 'lm_studio'" class="grid gap-4 md:grid-cols-2">
      <label class="block">
        <span class="text-sm font-medium text-slate-700">LM Studio base URL</span>
        <input
          :value="props.modelValue.lmStudioUrl"
          type="url"
          autocomplete="off"
          class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          @input="update('lmStudioUrl', $event)"
        />
      </label>

      <label class="block">
        <span class="text-sm font-medium text-slate-700">LM Studio local model</span>
        <input
          :value="props.modelValue.lmStudioModel"
          type="text"
          list="lm-studio-model-options"
          autocomplete="off"
          placeholder="Validate or test to auto-fill"
          class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          @input="update('lmStudioModel', $event)"
        />
        <datalist id="lm-studio-model-options">
          <option v-for="model in lmStudioModels" :key="model" :value="model" />
        </datalist>
      </label>

      <div class="md:col-span-2">
        <button
          type="button"
          class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
          :disabled="lmStudioLoading"
          @click="$emit('test-lm-studio')"
        >
          {{ lmStudioLoading ? "Testing LM Studio..." : "Test LM Studio" }}
        </button>
      </div>
    </div>

    <div v-if="mode === 'ollama'" class="grid gap-4 md:grid-cols-2">
      <label class="block">
        <span class="text-sm font-medium text-slate-700">Ollama base URL</span>
        <input
          :value="props.modelValue.ollamaUrl"
          type="url"
          autocomplete="off"
          class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          @input="update('ollamaUrl', $event)"
        />
      </label>

      <label class="block">
        <span class="text-sm font-medium text-slate-700">Ollama local model</span>
        <input
          :value="props.modelValue.ollamaModel"
          type="text"
          list="ollama-model-options"
          autocomplete="off"
          placeholder="Validate or test to auto-fill"
          class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          @input="update('ollamaModel', $event)"
        />
        <datalist id="ollama-model-options">
          <option v-for="model in ollamaModels" :key="model" :value="model" />
        </datalist>
      </label>

      <div class="md:col-span-2">
        <button
          type="button"
          class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
          :disabled="ollamaLoading"
          @click="$emit('test-ollama')"
        >
          {{ ollamaLoading ? "Testing Ollama..." : "Test Ollama" }}
        </button>
      </div>
    </div>
  </section>
</template>
