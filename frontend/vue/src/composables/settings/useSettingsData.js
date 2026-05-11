import { ref } from "vue";

import { fetchSettings } from "../../api/settingsApi";

export function useSettingsData() {
  const settingsPayload = ref(null);
  const settingsLoading = ref(false);
  const settingsError = ref("");

  async function loadSettings() {
    settingsLoading.value = true;
    settingsError.value = "";
    try {
      settingsPayload.value = await fetchSettings();
      return settingsPayload.value;
    } catch (error) {
      settingsError.value = error?.message || "Settings could not be loaded.";
      throw error;
    } finally {
      settingsLoading.value = false;
    }
  }

  return {
    settingsPayload,
    settingsLoading,
    settingsError,
    loadSettings,
  };
}
