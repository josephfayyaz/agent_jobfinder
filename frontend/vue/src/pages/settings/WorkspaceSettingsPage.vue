<script setup>
import { onMounted } from "vue";

import CvSettingsForm from "../../components/settings/CvSettingsForm.vue";
import GmailIntegrationPanel from "../../components/settings/GmailIntegrationPanel.vue";
import SearchPreferencesForm from "../../components/settings/SearchPreferencesForm.vue";
import SettingsPageShell from "../../components/settings/SettingsPageShell.vue";
import WorkspaceMaintenancePanel from "../../components/settings/WorkspaceMaintenancePanel.vue";
import { useWorkspaceSettings } from "../../composables/settings/useWorkspaceSettings";

const workspace = useWorkspaceSettings();

onMounted(() => {
  workspace.loadWorkspaceSettings();
});
</script>

<template>
  <SettingsPageShell
    title="Workspace Settings"
    description="Tune search preferences, Gmail intake, CV thresholds, and local workspace maintenance."
  >
    <div v-if="workspace.settingsLoading.value" class="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-600 shadow-sm">
      Loading workspace settings...
    </div>

    <div v-else class="space-y-5">
      <div
        v-if="workspace.settingsError.value"
        class="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
      >
        {{ workspace.settingsError.value }}
      </div>

      <SearchPreferencesForm
        :search="workspace.search"
        :role-count="workspace.roleCount.value"
        :role-limit-exceeded="workspace.roleLimitExceeded.value"
        :language-options="workspace.languageOptions.value"
        :language-level-options="workspace.languageLevelOptions.value"
        :status="workspace.searchStatus"
        :saving="workspace.searchSaving.value"
        :suggestions-loading="workspace.suggestionsLoading.value"
        @update:field="workspace.updateSearchField"
        @add-language="workspace.addLanguageRow"
        @remove-language="workspace.removeLanguageRow"
        @update-language="workspace.updateLanguageRow"
        @refresh-suggestions="workspace.refreshRoleSuggestions"
        @save-search="workspace.saveSearchSettings"
      />

      <GmailIntegrationPanel
        :gmail="workspace.gmail"
        :status="workspace.gmailStatus"
        :saving="workspace.gmailSaving.value"
        @update:field="workspace.updateGmailField"
        @save="workspace.saveGmailSettings"
        @connect-gmail="workspace.connectGmail"
        @disconnect-gmail="workspace.disconnectGmail"
      />

      <CvSettingsForm
        :cv="workspace.cv"
        :status="workspace.cvStatus"
        :saving="workspace.cvSaving.value"
        @update:field="workspace.updateCvField"
        @save="workspace.saveCvSettings"
      />

      <WorkspaceMaintenancePanel
        :maintenance="workspace.maintenance"
        :maintenance-status="workspace.maintenanceStatus"
        :reset-status="workspace.resetStatus"
        :delete-status="workspace.deleteStatus"
        :busy="workspace.maintenanceBusy.value"
        @update:field="workspace.updateMaintenanceField"
        @reload-settings="workspace.reloadRuntimeSettings"
        @copy-share="workspace.copyShareLink"
        @run-danger-action="workspace.runDangerAction"
      />
    </div>
  </SettingsPageShell>
</template>
