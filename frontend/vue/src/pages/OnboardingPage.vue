<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";

import FactsStep from "../components/onboarding/FactsStep.vue";
import OnboardingDonePanel from "../components/onboarding/OnboardingDonePanel.vue";
import OnboardingStepCards from "../components/onboarding/OnboardingStepCards.vue";
import ProviderStep from "../components/onboarding/ProviderStep.vue";
import QuestionsStep from "../components/onboarding/QuestionsStep.vue";
import ReviewStep from "../components/onboarding/ReviewStep.vue";
import SearchStep from "../components/onboarding/SearchStep.vue";
import { useFactsIntake } from "../composables/onboarding/useFactsIntake";
import { useOnboardingState } from "../composables/onboarding/useOnboardingState";
import { useProfileReview } from "../composables/onboarding/useProfileReview";
import { useProviderSetup } from "../composables/onboarding/useProviderSetup";
import { useQuestionIntake } from "../composables/onboarding/useQuestionIntake";
import { useSearchFocus } from "../composables/onboarding/useSearchFocus";

const currentStep = ref("ai");
const candidateId = ref("");
const donePanelVisible = ref(false);
const router = useRouter();

const readinessByStep = computed(() => ({
  ai: provider.providerReady.value,
  facts: facts.factsReady.value,
  questions: questions.questionsReady.value,
  review: review.reviewReady.value,
  search: search.searchReady.value,
}));

const onboarding = useOnboardingState({ currentStep, readinessByStep });

const provider = useProviderSetup({
  currentStep,
  setupData: onboarding.setupData,
  onboardingData: onboarding.onboardingData,
});

let review;
let search;

const questions = useQuestionIntake({
  candidateId,
  currentStep,
  setupData: onboarding.setupData,
  onboardingData: onboarding.onboardingData,
  openReviewStep: async () => review.openReviewStep(),
  markReviewUnsaved: () => {
    if (review) review.reviewSaved.value = false;
  },
});

search = useSearchFocus({
  candidateId,
  currentStep,
  donePanelVisible,
  setupData: onboarding.setupData,
  onboardingData: onboarding.onboardingData,
  onComplete: () => router.push("/dashboard"),
});

review = useProfileReview({
  candidateId,
  currentStep,
  setupData: onboarding.setupData,
  onboardingData: onboarding.onboardingData,
  openSearchStep: search.openSearchStep,
  markQuestionsAnswered: () => {
    questions.questionsAnswered.value = true;
  },
});

const facts = useFactsIntake({
  candidateId,
  currentStep,
  setupData: onboarding.setupData,
  onboardingData: onboarding.onboardingData,
  setIntakeQuestions: questions.setIntakeQuestions,
  openReviewStep: review.openReviewStep,
});

function selectStep(stepKey) {
  const step = onboarding.displaySteps.value.find((item) => item.key === stepKey);
  if (!step || step.disabled) return;

  if (stepKey === "review") {
    void review.openReviewStep();
    return;
  }

  if (stepKey === "search") {
    void search.openSearchStep();
    return;
  }

  currentStep.value = stepKey;
}
</script>

<template>
  <section class="mx-auto max-w-6xl space-y-6 pb-10">
    <header class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <p class="text-sm font-semibold uppercase tracking-wide text-sky-700">Setup flow</p>
      <div class="mt-3 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 class="text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            Set up Agent Jobfinder
          </h1>
          <p class="mt-3 max-w-3xl text-sm leading-6 text-slate-600 sm:text-base">
            Complete the provider, fact sheet, review, and search-focus steps in order. Each step
            unlocks only after its existing validation and save work succeeds.
          </p>
        </div>
        <div
          v-if="onboarding.loadError.value"
          class="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
          role="alert"
        >
          {{ onboarding.loadError.value }}
        </div>
      </div>
    </header>

    <template v-if="!donePanelVisible">
      <OnboardingStepCards
        :steps="onboarding.displaySteps.value"
        @select="selectStep"
      />

      <ProviderStep
        v-if="currentStep === 'ai'"
        :provider="provider"
      />

      <FactsStep
        v-else-if="currentStep === 'facts'"
        :facts="facts"
        @back="selectStep('ai')"
      />

      <QuestionsStep
        v-else-if="currentStep === 'questions'"
        :questions="questions"
        @back="selectStep('facts')"
      />

      <ReviewStep
        v-else-if="currentStep === 'review'"
        :review="review"
        :has-questions="questions.normalizedQuestions.value.length > 0"
        @back="selectStep(questions.normalizedQuestions.value.length ? 'questions' : 'facts')"
      />

      <SearchStep
        v-else-if="currentStep === 'search'"
        :search="search"
        @back="selectStep('review')"
      />

      <section
        v-else
        class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div class="max-w-2xl">
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {{ onboarding.displaySteps.value.find((step) => step.key === currentStep)?.label }}
          </p>
          <h2 class="mt-2 text-2xl font-semibold text-slate-950">
            {{ onboarding.displaySteps.value.find((step) => step.key === currentStep)?.title }}
          </h2>
          <p class="mt-2 text-sm leading-6 text-slate-600">
            This step is not available in the current setup flow state. Return to the previous
            completed step and finish its required action before continuing.
          </p>
        </div>
      </section>
    </template>
    <OnboardingDonePanel
      v-else
      :track-status="search.trackStatus.value"
    />
  </section>
</template>
