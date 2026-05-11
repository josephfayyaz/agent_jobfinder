<script setup>
import { onMounted } from "vue";

import LocalProviderPanel from "../../components/settings/LocalProviderPanel.vue";
import ProviderCredentialsForm from "../../components/settings/ProviderCredentialsForm.vue";
import ProviderModeSelector from "../../components/settings/ProviderModeSelector.vue";
import ProviderValidationStatus from "../../components/settings/ProviderValidationStatus.vue";
import SettingsPageShell from "../../components/settings/SettingsPageShell.vue";
import { useProviderSettings } from "../../composables/settings/useProviderSettings";

const provider = useProviderSettings();

onMounted(() => {
  provider.loadProviderSettings();
});
</script>

<template>
  <SettingsPageShell
    title="Settings"
    description="Configure the AI provider used for intake, scoring, and generated drafts."
  >
    <div v-if="provider.settingsLoading.value" class="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-600 shadow-sm">
      Loading provider settings...
    </div>

    <div v-else class="space-y-5">
      <div
        v-if="provider.settingsError.value"
        class="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
      >
        {{ provider.settingsError.value }}
      </div>

      <ProviderModeSelector
        v-model="provider.selectedProvider.value"
        :providers="provider.PROVIDERS"
      />

      <ProviderCredentialsForm
        :mode="provider.selectedProvider.value"
        :model-value="provider.providerForm"
        :configured="provider.configured"
        @update:field="provider.updateProviderField"
      />

      <LocalProviderPanel
        :mode="provider.selectedProvider.value"
        :model-value="provider.providerForm"
        :lm-studio-models="provider.lmStudioModels.value"
        :ollama-models="provider.ollamaModels.value"
        :lm-studio-loading="provider.lmStudioLoading.value"
        :ollama-loading="provider.ollamaLoading.value"
        @update:field="provider.updateProviderField"
        @test-lm-studio="provider.testLmStudio"
        @test-ollama="provider.testOllama"
      />

      <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <ProviderValidationStatus :status="provider.status" />
          <div class="flex flex-wrap gap-3">
            <button
              type="button"
              class="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
              :disabled="provider.busy.value"
              @click="provider.saveProviderSettings"
            >
              {{ provider.saving.value ? "Saving..." : "Save" }}
            </button>
            <button
              type="button"
              class="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              :disabled="provider.busy.value"
              @click="provider.validateSelectedProvider"
            >
              {{ provider.validating.value ? "Validating..." : "Validate Selected Provider" }}
            </button>
          </div>
        </div>
      </section>
    </div>
  </SettingsPageShell>
</template>
