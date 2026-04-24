let _parsedJob = null;
let _gaps = [];
let _questions = [];
let _taskId = null;
let _pollInterval = null;

async function submitJobText(evt) {
  const text = document.getElementById("job-text-input").value.trim();
  const errEl = document.getElementById("step1-error");
  errEl.classList.add("hidden");
  if (!text) {
    errEl.textContent = "Please paste some job info first.";
    errEl.classList.remove("hidden");
    return;
  }

  const btn = evt.currentTarget;
  btn.disabled = true;
  btn.textContent = "Parsing...";

  try {
    const response = await fetch("/apply/parse", {
      method: "POST",
      headers: {"Content-Type": "application/x-www-form-urlencoded"},
      body: new URLSearchParams({job_text: text}),
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const data = await response.json();
    _parsedJob = data.job;
    _gaps = data.gaps || [];
    showStep2(data);
  } catch (err) {
    errEl.textContent = "Error: " + err.message;
    errEl.classList.remove("hidden");
    btn.disabled = false;
    btn.textContent = "Parse & Score ->";
  }
}

function showStep2(data) {
  document.getElementById("step1").classList.add("hidden");
  document.getElementById("step2").classList.remove("hidden");
  document.getElementById("step2-ind").classList.remove("text-slate-400");
  document.getElementById("step2-ind").classList.add("font-semibold", "text-indigo-600");

  const score = data.score ?? "-";
  document.getElementById("score-badge").textContent = score + "/100";
  document.getElementById("score-summary").textContent = data.summary || "";

  const matchedList = document.getElementById("matched-list");
  const gapsList = document.getElementById("gaps-list");
  matchedList.innerHTML = "";
  (data.matched || []).slice(0, 6).forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    matchedList.appendChild(li);
  });
  gapsList.innerHTML = "";
  (data.gaps || []).forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    gapsList.appendChild(li);
  });
}

async function proceedToQuestions() {
  document.getElementById("step2").classList.add("hidden");
  document.getElementById("step3-ind").classList.remove("text-slate-400");
  document.getElementById("step3-ind").classList.add("font-semibold", "text-indigo-600");

  if (_gaps.length === 0) {
    await generateDraft();
    return;
  }

  const response = await fetch("/apply/questions", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({job: _parsedJob, gaps: _gaps}),
  });
  const data = await response.json();
  _questions = data.questions || [];
  renderQuestions();
  document.getElementById("step3").classList.remove("hidden");
}

function renderQuestions() {
  const container = document.getElementById("questions-container");
  container.innerHTML = "";
  _questions.forEach((question, index) => {
    const card = document.createElement("div");
    card.className = "space-y-2 rounded-lg border border-slate-200 p-4";

    const gapEl = document.createElement("p");
    gapEl.className = "text-xs font-semibold uppercase text-slate-500";
    gapEl.textContent = "Gap: " + question.gap;

    const questionEl = document.createElement("p");
    questionEl.className = "text-sm font-medium text-slate-700";
    questionEl.textContent = question.question;

    const whyEl = document.createElement("p");
    whyEl.className = "text-xs italic text-slate-400";
    whyEl.textContent = question.why;

    const input = document.createElement("input");
    input.type = "text";
    input.id = "answer-" + index;
    input.className = "w-full rounded border border-slate-300 px-3 py-1.5 text-sm focus:ring-2 focus:ring-indigo-400";
    input.placeholder = "Your answer (or leave blank to skip)";

    card.appendChild(gapEl);
    card.appendChild(questionEl);
    card.appendChild(whyEl);
    card.appendChild(input);
    container.appendChild(card);
  });
}

async function generateDraft() {
  document.getElementById("step3").classList.add("hidden");
  document.getElementById("step4").classList.remove("hidden");
  document.getElementById("step4-ind").classList.remove("text-slate-400");
  document.getElementById("step4-ind").classList.add("font-semibold", "text-indigo-600");

  const answers = _questions.map((question, index) => {
    const answer = (document.getElementById(`answer-${index}`)?.value || "").trim();
    return {gap: question.gap, question_id: question.id || `q${index}`, answer, confirmed: !!answer};
  });
  const trackSlug = document.getElementById("track-select")?.value || "";

  const response = await fetch("/apply/generate", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({job: _parsedJob, answers, track_slug: trackSlug}),
  });
  const data = await response.json();
  _taskId = data.task_id;
  startPolling();
}

function startPolling() {
  _pollInterval = setInterval(async () => {
    const response = await fetch(`/apply/status/${_taskId}`);
    const data = await response.json();
    const statusEl = document.getElementById("status-text");
    statusEl.textContent = `Status: ${data.status}`;
    if (data.status === "completed" && data.draft_id) {
      clearInterval(_pollInterval);
      window.location.href = `/ui/drafts/${data.draft_id}`;
    } else if (data.status === "failed") {
      clearInterval(_pollInterval);
      statusEl.textContent = "Generation failed. Check the worker logs.";
    }
  }, 3000);
}
