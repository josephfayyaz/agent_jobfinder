import { computed, ref } from "vue";

import { answerCandidateIntake } from "../../services/onboardingApi";
import { createEmptyQuestionAnswer, normalizeQuestion } from "../../utils/onboardingNormalizers";

export function useQuestionIntake({
  candidateId,
  currentStep,
  setupData,
  onboardingData,
  openReviewStep,
  markReviewUnsaved,
}) {
  const intakeQuestions = ref([]);
  const questionAnswers = ref({});
  const questionsBusy = ref(false);
  const questionsStatus = ref("");
  const questionsStatusError = ref(false);
  const questionsAnswered = ref(false);

  const normalizedQuestions = computed(() =>
    intakeQuestions.value.map((question, index) => normalizeQuestion(question, index)),
  );

  const questionsReady = computed(() =>
    Boolean(
      questionsAnswered.value ||
        setupData.value?.questions_ready ||
        onboardingData.value?.questions_ready,
    ),
  );

  function setQuestionsStatus(message, isError = false) {
    questionsStatus.value = message;
    questionsStatusError.value = isError;
  }

  function setIntakeQuestions(questions) {
    const nextQuestions = Array.isArray(questions) ? questions : [];
    const nextAnswers = {};

    nextQuestions.forEach((question, index) => {
      const normalized = normalizeQuestion(question, index);
      nextAnswers[normalized.id] = createEmptyQuestionAnswer();
    });

    intakeQuestions.value = nextQuestions;
    questionAnswers.value = nextAnswers;
    questionsAnswered.value = false;
    markReviewUnsaved?.();
    setQuestionsStatus("");
  }

  function buildAnswersPayload() {
    const answers = {};
    const missingPrompts = [];

    normalizedQuestions.value.forEach((question) => {
      const answer = questionAnswers.value[question.id] || createEmptyQuestionAnswer();

      if (question.kind === "single_select") {
        const note = String(answer.text || "").trim();
        const value = note || answer.selected || "";
        answers[question.id] = value;
        if (question.required && !value) missingPrompts.push(question.prompt);
        return;
      }

      if (question.kind === "multi_select") {
        const choices = Array.isArray(answer.choices) ? answer.choices.filter(Boolean) : [];
        const note = String(answer.text || "").trim();
        const value = note ? [...choices, note] : choices;
        answers[question.id] = value;
        if (question.required && !value.length) missingPrompts.push(question.prompt);
        return;
      }

      const value = String(answer.text || "").trim();
      answers[question.id] = value;
      if (question.required && !value) missingPrompts.push(question.prompt);
    });

    return { answers, missingPrompts };
  }

  async function submitQuestionAnswers() {
    if (!candidateId.value) {
      setQuestionsStatus(
        "Could not find the onboarding profile shell. Return to Facts and run intake again.",
        true,
      );
      currentStep.value = "questions";
      return;
    }

    const { answers, missingPrompts } = buildAnswersPayload();

    if (missingPrompts.length) {
      setQuestionsStatus(`Please answer the required questions first. Missing: ${missingPrompts[0]}`, true);
      currentStep.value = "questions";
      return;
    }

    questionsBusy.value = true;
    setQuestionsStatus("Saving your answers...");

    try {
      const data = await answerCandidateIntake(candidateId.value, answers);

      if (data?.status === "questions_needed" && Array.isArray(data.questions) && data.questions.length) {
        setIntakeQuestions(data.questions);
        setQuestionsStatus("More detail is still needed. Answer the updated questions below.");
        currentStep.value = "questions";
        return;
      }

      questionAnswers.value = {};
      intakeQuestions.value = [];
      setQuestionsStatus("Answers saved.");
      await openReviewStep();
    } catch (error) {
      setQuestionsStatus(error?.message || "Saving answers failed.", true);
      currentStep.value = "questions";
    } finally {
      questionsBusy.value = false;
    }
  }

  return {
    intakeQuestions,
    normalizedQuestions,
    questionAnswers,
    questionsBusy,
    questionsStatus,
    questionsStatusError,
    questionsAnswered,
    questionsReady,
    setIntakeQuestions,
    submitQuestionAnswers,
  };
}
