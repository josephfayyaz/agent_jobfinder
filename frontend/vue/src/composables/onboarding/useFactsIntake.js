import { computed, ref } from "vue";

import {
  ensureCandidateShellApi,
  startCandidateIntake,
  uploadCandidateSources,
} from "../../services/onboardingApi";
import { formatFileSize } from "../../utils/onboardingFormatters";

const SUPPORTED_SOURCE_EXTENSIONS = [".pdf", ".txt", ".md", ".rst"];
const SUPPORTED_SOURCE_TYPES = ["application/pdf", "text/plain", "text/markdown"];

function isSupportedSourceFile(file) {
  const name = String(file?.name || "").toLowerCase();
  const type = String(file?.type || "").toLowerCase();

  return (
    SUPPORTED_SOURCE_EXTENSIONS.some((extension) => name.endsWith(extension)) ||
    SUPPORTED_SOURCE_TYPES.includes(type)
  );
}

export function useFactsIntake({ candidateId, currentStep, setupData, onboardingData, setIntakeQuestions, openReviewStep }) {
  const sourceFiles = ref([]);
  const profileNotes = ref("");
  const factsBusy = ref(false);
  const factsStatus = ref("");
  const factsStatusError = ref(false);
  const factsSaved = ref(false);

  const factsReady = computed(() =>
    Boolean(
      factsSaved.value ||
        setupData.value?.facts_ready ||
        setupData.value?.fact_sheet_ready ||
        onboardingData.value?.facts_ready ||
        onboardingData.value?.fact_sheet_ready,
    ),
  );

  const selectedFileNames = computed(() =>
    sourceFiles.value.map((file) => `${file.name} (${formatFileSize(file.size)})`),
  );

  function setFactsStatus(message, isError = false) {
    factsStatus.value = message;
    factsStatusError.value = isError;
  }

  function handleSourceFiles(event) {
    sourceFiles.value = Array.from(event.target?.files || []);
    factsSaved.value = false;
    setIntakeQuestions([]);
    setFactsStatus("");
  }

  async function ensureCandidateShell() {
    if (candidateId.value) return candidateId.value;

    const candidate = await ensureCandidateShellApi();
    candidateId.value = candidate?.id || "";

    if (!candidateId.value) {
      throw new Error("Could not prepare the onboarding profile shell.");
    }

    return candidateId.value;
  }

  async function uploadSourceFiles(files) {
    if (!files.length) return;

    const uploadData = new FormData();
    uploadData.append("replace_existing", "1");
    files.forEach((file) => uploadData.append("files", file));

    await uploadCandidateSources(candidateId.value, uploadData);
  }

  async function runFactsIntake() {
    setFactsStatus("");
    factsSaved.value = false;
    setIntakeQuestions([]);

    try {
      await ensureCandidateShell();
    } catch (error) {
      setFactsStatus(error?.message || "Could not prepare the onboarding profile shell.", true);
      return;
    }

    const files = sourceFiles.value;
    const notes = profileNotes.value.trim();

    if (!files.length && !notes) {
      setFactsStatus("Upload at least one CV file (PDF/TXT/MD/RST) or add manual notes.", true);
      return;
    }

    const invalidFiles = files.filter((file) => !isSupportedSourceFile(file));
    if (invalidFiles.length) {
      setFactsStatus("Only PDF, TXT, MD, or RST files are accepted in onboarding intake.", true);
      return;
    }

    factsBusy.value = true;
    setFactsStatus("Analysing your profile...");

    try {
      await uploadSourceFiles(files);
      const intakeData = await startCandidateIntake(candidateId.value, notes);
      factsSaved.value = true;

      if (
        intakeData?.status === "questions_needed" &&
        Array.isArray(intakeData.questions) &&
        intakeData.questions.length
      ) {
        setIntakeQuestions(intakeData.questions);
        setFactsStatus("Profile intake saved. Answer the remaining questions.");
        currentStep.value = "questions";
        return;
      }

      setFactsStatus("Profile intake saved.");
      await openReviewStep();
    } catch (error) {
      setFactsStatus(error?.message || "Profile intake failed.", true);
      currentStep.value = "facts";
    } finally {
      factsBusy.value = false;
    }
  }

  return {
    sourceFiles,
    profileNotes,
    factsBusy,
    factsStatus,
    factsStatusError,
    factsSaved,
    factsReady,
    selectedFileNames,
    handleSourceFiles,
    runFactsIntake,
    ensureCandidateShell,
  };
}
