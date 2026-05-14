import { defineStore } from "pinia";

export const useSetupStore = defineStore("setup", {
  state: () => ({
    loaded: true,
    setupComplete: true,
    providerConfigured: true
  }),

  getters: {
    requiresSetup: (state) => !state.setupComplete || !state.providerConfigured
  },

  actions: {
    markLoaded() {
      this.loaded = true;
    }
  }
});
