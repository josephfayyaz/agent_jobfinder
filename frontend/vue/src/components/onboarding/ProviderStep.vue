<script setup>
import StatusMessage from "./StatusMessage.vue";

defineProps({
  provider: { type: Object, required: true },
});
</script>

<template>
  <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
    <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">AI provider</p>
        <h2 class="mt-1 text-2xl font-semibold text-slate-950">Choose and validate a provider</h2>
      </div>
    </div>

    <div class="mt-5 grid gap-3 md:grid-cols-5">
      <button
        v-for="item in provider.PROVIDERS"
        :key="item.value"
        type="button"
        class="setup-provider-card rounded-lg border bg-white p-4 text-left transition hover:border-sky-300 hover:bg-sky-50/50"
        :class="provider.selectedProvider.value === item.value ? 'border-sky-500 bg-sky-50 ring-2 ring-sky-100' : 'border-slate-200'"
        @click="provider.selectProvider(item.value)"
      >
        <span class="text-xs font-semibold uppercase tracking-wide text-slate-500">{{ item.eyebrow }}</span>
        <span class="mt-2 block text-base font-semibold text-slate-950">{{ item.label }}</span>
        <span class="mt-1 block text-sm leading-5 text-slate-600">{{ item.description }}</span>
      </button>
    </div>

    <div class="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p v-if="!provider.selectedProvider.value" class="text-sm text-slate-600">
        Select a provider to show its connection fields.
      </p>

      <div v-if="provider.selectedProvider.value === 'lm_studio'" class="grid gap-4 md:grid-cols-2">
        <label class="block">
          <span class="text-sm font-medium text-slate-700">Gateway URL</span>
          <input
            v-model.trim="provider.providerForm.value.lmStudioUrl"
            class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            type="url"
            autocomplete="off"
          />
        </label>

        <label class="block">
          <span class="text-sm font-medium text-slate-700">Chat model</span>
          <select
            v-model="provider.providerForm.value.lmStudioModel"
            class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          >
            <option value="">Auto-select after validation</option>
            <option
              v-for="model in provider.nonEmbeddingModels(provider.lmStudioModels.value)"
              :key="model"
              :value="model"
            >
              {{ model }}
            </option>
          </select>
        </label>
      </div>

      <div v-if="provider.selectedProvider.value === 'ollama'" class="grid gap-4 md:grid-cols-2">
        <label class="block">
          <span class="text-sm font-medium text-slate-700">Ollama URL</span>
          <input
            v-model.trim="provider.providerForm.value.ollamaUrl"
            class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            type="url"
            autocomplete="off"
          />
        </label>

        <label class="block">
          <span class="text-sm font-medium text-slate-700">Chat model</span>
          <input
            v-model.trim="provider.providerForm.value.ollamaModel"
            class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            type="text"
            list="ollama-model-options"
            placeholder="Auto-select after validation"
            autocomplete="off"
          />
          <datalist id="ollama-model-options">
            <option
              v-for="model in provider.nonEmbeddingModels(provider.ollamaModels.value)"
              :key="model"
              :value="model"
            />
          </datalist>
        </label>
      </div>

      <div v-if="provider.selectedProvider.value === 'openai'" class="max-w-xl">
        <label class="block">
          <span class="text-sm font-medium text-slate-700">OpenAI API key</span>
          <input
            v-model.trim="provider.providerForm.value.openaiKey"
            class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            type="password"
            placeholder="Leave blank to keep the existing key"
            autocomplete="off"
          />
        </label>
      </div>

      <div v-if="provider.selectedProvider.value === 'anthropic'" class="max-w-xl">
        <label class="block">
          <span class="text-sm font-medium text-slate-700">Anthropic API key</span>
          <input
            v-model.trim="provider.providerForm.value.anthropicKey"
            class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            type="password"
            placeholder="Leave blank to keep the existing key"
            autocomplete="off"
          />
        </label>
      </div>

      <div v-if="provider.selectedProvider.value === 'gemini'" class="max-w-xl">
        <label class="block">
          <span class="text-sm font-medium text-slate-700">Gemini API key</span>
          <input
            v-model.trim="provider.providerForm.value.geminiKey"
            class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            type="password"
            placeholder="Leave blank to keep the existing key"
            autocomplete="off"
          />
        </label>
      </div>
    </div>

    <div class="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <StatusMessage
        :message="provider.providerStatus.value"
        :is-error="provider.providerStatusError.value"
        success-class="text-emerald-700"
      />
      <button
        type="button"
        class="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        :disabled="provider.providerBusy.value"
        @click="provider.validateAndSaveProvider"
      >
        {{ provider.providerBusy.value ? "Validating..." : "Validate & Continue" }}
      </button>
    </div>
  </section>
</template>
