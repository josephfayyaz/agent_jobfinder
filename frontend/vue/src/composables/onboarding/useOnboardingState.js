import { computed, onMounted, ref } from "vue";

import { loadOnboardingStateBundle } from "../../services/onboardingApi";

export const SETUP_STEPS = [
  {
    key: "ai",
    label: "AI",
    title: "Connect an AI provider",
    description: "Validate and save the provider used by the local job agent.",
  },
  {
    key: "facts",
    label: "Facts",
    title: "Add your fact sheet",
    description: "Upload documents or notes so the agent can build your profile.",
  },
  {
    key: "questions",
    label: "Questions",
    title: "Answer follow-up questions",
    description: "Resolve missing profile evidence before review.",
  },
  {
    key: "review",
    label: "Review",
    title: "Review your profile",
    description: "Check extracted facts before saving profile memory.",
  },
  {
    key: "search",
    label: "Search",
    title: "Configure search focus",
    description: "Choose target roles, countries, seniority, and languages.",
  },
];

export function useOnboardingState({ currentStep, readinessByStep }) {
  const onboardingState = ref(null);
  const onboardingSteps = ref(null);
  const setupState = ref(null);
  const loadError = ref("");
  const isLoading = ref(true);

  const onboardingData = computed(() => onboardingState.value?.data || onboardingState.value || {});
  const onboardingStepsData = computed(
    () => onboardingSteps.value?.data || onboardingSteps.value || {},
  );
  const setupData = computed(() => setupState.value?.data || setupState.value || {});

  const stepStateByKey = computed(() => {
    const state = new Map();
    const steps = Array.isArray(onboardingStepsData.value?.items)
      ? onboardingStepsData.value.items
      : onboardingStepsData.value?.steps;

    if (Array.isArray(steps)) {
      steps.forEach((step) => {
        const key = step.key || step.id || step.name;
        if (key) state.set(key, step);
      });
    }

    return state;
  });

  const displaySteps = computed(() => {
    const stepCompletion = SETUP_STEPS.map((step) => {
      const apiStep = stepStateByKey.value.get(step.key) || {};
      return Boolean(
        readinessByStep.value[step.key] || apiStep.completed || apiStep.done || apiStep.ready,
      );
    });
    const firstIncompleteIndex = stepCompletion.findIndex((completed) => !completed);
    const unlockedUntilIndex =
      firstIncompleteIndex === -1 ? SETUP_STEPS.length - 1 : firstIncompleteIndex;

    return SETUP_STEPS.map((step, index) => {
      const completed = stepCompletion[index];
      const active = currentStep.value === step.key;
      const disabled = !active && !completed && index > unlockedUntilIndex;

      return {
        ...step,
        index: index + 1,
        active,
        completed,
        disabled,
        clickable: active || completed || !disabled,
        statusText: completed ? "Complete" : active ? "Current" : disabled ? "Locked" : "Next",
      };
    });
  });

  async function loadOnboardingState() {
    isLoading.value = true;
    loadError.value = "";

    try {
      const [onboarding, steps, setup] = await loadOnboardingStateBundle();
      onboardingState.value = onboarding;
      onboardingSteps.value = steps;
      setupState.value = setup;
    } catch (error) {
      loadError.value = error?.message || "Unable to load onboarding state.";
    } finally {
      isLoading.value = false;
    }
  }

  onMounted(loadOnboardingState);

  return {
    onboardingState,
    onboardingSteps,
    setupState,
    onboardingData,
    setupData,
    loadError,
    isLoading,
    displaySteps,
    loadOnboardingState,
  };
}
