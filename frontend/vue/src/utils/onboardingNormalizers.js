export function normalizeQuestion(question, index) {
  const questionObj =
    typeof question === "string"
      ? {
          id: `q${index + 1}`,
          prompt: question,
          kind: "text",
          options: [],
          allow_free_text: true,
        }
      : question || {};

  const kind = ["text", "single_select", "multi_select"].includes(questionObj.kind)
    ? questionObj.kind
    : "text";

  return {
    id: String(questionObj.id || `q${index + 1}`),
    prompt: String(
      questionObj.prompt || questionObj.question || questionObj.id || `Question ${index + 1}`,
    ),
    kind,
    options: Array.isArray(questionObj.options)
      ? questionObj.options.filter(Boolean).map(String)
      : [],
    allow_free_text: Boolean(questionObj.allow_free_text),
    required: questionObj.required !== false,
  };
}

export function createEmptyQuestionAnswer() {
  return { text: "", selected: "", choices: [] };
}

export function normalizeSearchLanguages(rows = []) {
  const normalized = [];

  rows.forEach((row) => {
    const name = String(row?.name || "").trim();
    const level = String(row?.level || "").trim() || "professional";

    if (!name) return;

    const exists = normalized.some(
      (item) => item.name.toLowerCase() === name.toLowerCase(),
    );

    if (!exists) normalized.push({ name, level });
  });

  return normalized.length ? normalized : [{ name: "English", level: "professional" }];
}
