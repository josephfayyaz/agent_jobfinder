import { computed, ref } from "vue";

import { loadCandidateReview, saveCandidateFactSheet } from "../../services/onboardingApi";
import { clonePlainObject, splitLines } from "../../utils/onboardingFormatters";

export function createEmptyReviewForm() {
  return {
    fullName: "",
    email: "",
    education: [],
    experience: [],
    projects: [],
    skillsText: "",
    languages: [],
  };
}

function readFromFactSheetSkills(factSheet) {
  const skills = factSheet?.skills;
  if (!skills || typeof skills !== "object") return [];

  const rows = [];
  Object.values(skills).forEach((value) => {
    if (!Array.isArray(value)) return;
    value.forEach((item) => {
      const text = String(item || "").trim();
      if (text && !rows.includes(text)) rows.push(text);
    });
  });

  return rows;
}

function buildReviewForm(factSheet) {
  const person = factSheet?.person || {};
  const contact = person.contact || {};

  const education = Array.isArray(factSheet?.education)
    ? factSheet.education.map((item) => ({
        ...clonePlainObject(item),
        degree: item?.degree || "",
        field: item?.field || "",
        institution: item?.institution || "",
        status: item?.status || "",
      }))
    : [];

  const experience = Array.isArray(factSheet?.experience)
    ? factSheet.experience.map((item) => ({
        ...clonePlainObject(item),
        role_title: item?.role_title || "",
        organization: item?.organization || "",
        start_date: item?.start_date || "",
        end_date: item?.end_date || "",
        responsibilities_text: Array.isArray(item?.responsibilities)
          ? item.responsibilities.join("\n")
          : String(item?.responsibilities || ""),
      }))
    : [];

  const projects = Array.isArray(factSheet?.projects)
    ? factSheet.projects.map((item) => ({
        ...clonePlainObject(item),
        name: item?.name || "",
        link: item?.link || "",
        summary: item?.summary || (Array.isArray(item?.key_results) ? item.key_results.join("\n") : ""),
      }))
    : [];

  const languages = Array.isArray(factSheet?.languages) && factSheet.languages.length
    ? factSheet.languages.map((item) => ({
        ...clonePlainObject(item),
        name: item?.name || "",
        level: item?.level || "professional",
      }))
    : [{ name: "English", level: "professional" }];

  return {
    fullName: person.full_name || "",
    email: contact.email || "",
    education,
    experience,
    projects,
    skillsText: readFromFactSheetSkills(factSheet).join("\n"),
    languages,
  };
}

export function useProfileReview({ candidateId, currentStep, setupData, onboardingData, openSearchStep, markQuestionsAnswered }) {
  const reviewFactSheet = ref(null);
  const reviewReadiness = ref(null);
  const reviewForm = ref(createEmptyReviewForm());
  const reviewBusy = ref(false);
  const reviewSaving = ref(false);
  const reviewStatus = ref("");
  const reviewStatusError = ref(false);
  const reviewSaved = ref(false);

  const reviewReady = computed(() =>
    Boolean(reviewSaved.value || setupData.value?.review_ready || onboardingData.value?.review_ready),
  );

  const readinessBanner = computed(() => {
    const readiness = reviewReadiness.value;
    if (!readiness) return null;

    const status = readiness.status || "usable_with_warnings";
    const missing =
      Array.isArray(readiness.missing_sections) && readiness.missing_sections.length
        ? ` Missing: ${readiness.missing_sections.join(", ")}.`
        : "";
    const reason =
      (Array.isArray(readiness.reasons) && readiness.reasons[0]) ||
      "Review the extracted profile before continuing.";

    if (status === "ready") {
      return {
        title: "Profile Readiness: Ready",
        message: `${reason}${missing}`,
        tone: "border-emerald-200 bg-emerald-50 text-emerald-800",
      };
    }

    if (status === "insufficient_profile_data") {
      return {
        title: "Profile Readiness: Needs more evidence",
        message: `${reason}${missing}`,
        tone: "border-rose-200 bg-rose-50 text-rose-800",
      };
    }

    return {
      title: "Profile Readiness: Usable with warnings",
      message: `${reason}${missing}`,
      tone: "border-amber-200 bg-amber-50 text-amber-800",
    };
  });

  function setReviewStatus(message, isError = false) {
    reviewStatus.value = message;
    reviewStatusError.value = isError;
  }

  function addReviewRow(sectionId) {
    if (sectionId === "education") {
      reviewForm.value.education.push({ degree: "", field: "", institution: "", status: "" });
      return;
    }

    if (sectionId === "experience") {
      reviewForm.value.experience.push({
        role_title: "",
        organization: "",
        start_date: "",
        end_date: "",
        responsibilities_text: "",
        responsibilities: [],
      });
      return;
    }

    if (sectionId === "projects") {
      reviewForm.value.projects.push({ name: "", link: "", summary: "" });
    }
  }

  function removeReviewRow(sectionId, index) {
    if (!Array.isArray(reviewForm.value[sectionId])) return;
    reviewForm.value[sectionId].splice(index, 1);
  }

  function addReviewLanguage() {
    reviewForm.value.languages.push({ name: "", level: "professional" });
  }

  function removeReviewLanguage(index) {
    reviewForm.value.languages.splice(index, 1);
    if (!reviewForm.value.languages.length) addReviewLanguage();
  }

  function buildReviewedFactSheetPayload() {
    const base = clonePlainObject(reviewFactSheet.value);
    const form = reviewForm.value;

    const education = form.education
      .map((row) => ({
        ...clonePlainObject(row),
        degree: String(row.degree || "").trim(),
        field: String(row.field || "").trim(),
        institution: String(row.institution || "").trim(),
        status: String(row.status || "").trim(),
      }))
      .filter((row) => row.degree || row.field || row.institution);

    const experience = form.experience
      .map((row) => ({
        ...clonePlainObject(row),
        role_title: String(row.role_title || "").trim(),
        organization: String(row.organization || "").trim(),
        start_date: String(row.start_date || "").trim(),
        end_date: String(row.end_date || "").trim(),
        responsibilities: splitLines(row.responsibilities_text),
        tools: Array.isArray(row.tools) ? row.tools : [],
        achievements: Array.isArray(row.achievements) ? row.achievements : [],
        evidence_refs: Array.isArray(row.evidence_refs) ? row.evidence_refs : [],
      }))
      .filter((row) => row.role_title || row.organization || row.responsibilities.length);

    const projects = form.projects
      .map((row) => ({
        ...clonePlainObject(row),
        name: String(row.name || "").trim(),
        link: String(row.link || "").trim(),
        summary: String(row.summary || "").trim(),
        tools: Array.isArray(row.tools) ? row.tools : [],
      }))
      .filter((row) => row.name || row.summary);

    const languages = form.languages
      .map((row) => ({
        ...clonePlainObject(row),
        name: String(row.name || "").trim(),
        level: String(row.level || "").trim() || "professional",
      }))
      .filter((row) => row.name);

    return {
      ...base,
      person: {
        ...(base.person || {}),
        full_name: form.fullName.trim(),
        contact: {
          ...((base.person || {}).contact || {}),
          email: form.email.trim(),
        },
      },
      education,
      experience,
      projects,
      skills: { business_tools: splitLines(form.skillsText) },
      languages,
    };
  }

  async function loadProfileReview() {
    if (!candidateId.value) {
      reviewFactSheet.value = null;
      reviewReadiness.value = null;
      reviewForm.value = createEmptyReviewForm();
      setReviewStatus("Run intake before loading the profile review.", true);
      return false;
    }

    reviewBusy.value = true;
    setReviewStatus("Loading extracted profile review...");

    try {
      const data = await loadCandidateReview(candidateId.value);
      reviewFactSheet.value = data?.fact_sheet || {};
      reviewReadiness.value = data?.readiness || null;
      reviewForm.value = buildReviewForm(reviewFactSheet.value);
      markQuestionsAnswered?.();
      setReviewStatus("");
      return true;
    } catch (error) {
      reviewFactSheet.value = null;
      reviewReadiness.value = null;
      reviewForm.value = createEmptyReviewForm();
      setReviewStatus(error?.message || "Could not load the extracted profile review.", true);
      return false;
    } finally {
      reviewBusy.value = false;
    }
  }

  async function openReviewStep() {
    currentStep.value = "review";
    await loadProfileReview();
  }

  async function saveProfileReview() {
    if (!candidateId.value || !reviewFactSheet.value) {
      setReviewStatus("Run intake before saving the profile review.", true);
      currentStep.value = "review";
      return;
    }

    reviewSaving.value = true;
    setReviewStatus("Saving profile review...");

    try {
      const payload = buildReviewedFactSheetPayload();
      await saveCandidateFactSheet(candidateId.value, payload);
      reviewSaved.value = true;
      setReviewStatus("Profile review saved.");
      await loadProfileReview();
      await openSearchStep();
    } catch (error) {
      setReviewStatus(error?.message || "Saving profile review failed.", true);
      currentStep.value = "review";
    } finally {
      reviewSaving.value = false;
    }
  }

  return {
    reviewFactSheet,
    reviewReadiness,
    reviewForm,
    reviewBusy,
    reviewSaving,
    reviewStatus,
    reviewStatusError,
    reviewSaved,
    reviewReady,
    readinessBanner,
    addReviewRow,
    removeReviewRow,
    addReviewLanguage,
    removeReviewLanguage,
    loadProfileReview,
    openReviewStep,
    saveProfileReview,
  };
}
