<script setup>
import { computed, ref } from "vue";

import AppPageHeader from "../components/AppPageHeader.vue";
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
  <section class="space-y-8">
    <AppPageHeader
      eyebrow="Setup"
      title="Onboarding"
      description="The Vue onboarding flow is being migrated in small phases. Provider setup, profile intake, review, and search focus are available here."
    >
      <template #actions>
        <a
          class="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
          href="/ui/onboarding"
        >
          Complete setup in legacy UI
        </a>
      </template>
    </AppPageHeader>

    <OnboardingDonePanel
      v-if="donePanelVisible"
      :track-status="search.trackStatus.value"
    />

    <template v-else>
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
            This Vue step is still read-only during the migration. Continue in the legacy onboarding
            page to complete setup.
          </p>
          <a
            class="mt-4 inline-flex rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
            href="/ui/onboarding"
          >
            Open legacy onboarding
          </a>
        </div>
      </section>
    </template>
  </section>
</template>
