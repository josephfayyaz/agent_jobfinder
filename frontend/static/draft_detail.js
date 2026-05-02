let _currentClarificationId = null;
let _currentBulletTarget = null;

function _resetClarifyAcceptButton() {
  const acceptButton = document.getElementById("clarify-accept-btn");
  const promoteButton = document.getElementById("clarify-promote-btn");
  const status = document.getElementById("clarify-status");
  if (acceptButton) {
    acceptButton.textContent = "Apply to Draft";
    acceptButton.disabled = false;
  }
  if (promoteButton) {
    promoteButton.textContent = "Save for Future Drafts";
    promoteButton.disabled = true;
  }
  if (status) {
    status.textContent = "";
  }
}

async function rewriteBullet(btn, draftId, bullet, targetSection, targetItemIndex, targetBulletIndex) {
  const panel = document.getElementById("bullet-clarify-panel");
  const loading = document.getElementById("clarify-loading");
  const result = document.getElementById("clarify-result");
  const originalEl = document.getElementById("clarify-original");
  const rewriteEl = document.getElementById("clarify-rewrite");

  _currentClarificationId = null;
  _currentBulletTarget = btn.parentElement.querySelector("span");
  _resetClarifyAcceptButton();
  originalEl.textContent = bullet;
  rewriteEl.textContent = "";
  loading.classList.remove("hidden");
  result.classList.add("hidden");
  panel.scrollIntoView({behavior: "smooth", block: "nearest"});

  try {
    const response = await fetch(`/drafts/${draftId}/clarify`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        bullet,
        target_section: targetSection,
        target_item_index: targetItemIndex,
        target_bullet_index: targetBulletIndex,
      }),
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const data = await response.json();
    _currentClarificationId = data.id;
    rewriteEl.textContent = data.suggested_rewrite;
  } catch (err) {
    rewriteEl.textContent = `Error: ${err.message}`;
    document.getElementById("clarify-accept-btn").disabled = true;
  } finally {
    loading.classList.add("hidden");
    result.classList.remove("hidden");
  }
}

async function acceptRewrite() {
  if (!_currentClarificationId) {
    return;
  }
  const acceptButton = document.getElementById("clarify-accept-btn");
  const promoteButton = document.getElementById("clarify-promote-btn");
  const status = document.getElementById("clarify-status");
  const response = await fetch(`/drafts/clarifications/${_currentClarificationId}/accept`, {method: "POST"});
  if (!response.ok) {
    acceptButton.textContent = "Apply failed";
    return;
  }
  const rewritten = document.getElementById("clarify-rewrite").textContent;
  if (_currentBulletTarget) {
    _currentBulletTarget.textContent = rewritten;
  }
  acceptButton.textContent = "✓ Applied";
  acceptButton.disabled = true;
  promoteButton.disabled = false;
  status.textContent = "Draft updated. The rendered artifact was refreshed in the background.";
}

async function promoteRewrite() {
  if (!_currentClarificationId) {
    return;
  }
  const button = document.getElementById("clarify-promote-btn");
  const status = document.getElementById("clarify-status");
  const response = await fetch(`/drafts/clarifications/${_currentClarificationId}/promote`, {method: "POST"});
  if (!response.ok) {
    status.textContent = "Could not save for future drafts.";
    return;
  }
  button.textContent = "✓ Saved for Future";
  button.disabled = true;
  status.textContent = "This approved wording is now saved in your role-specific fact sheet bank for future drafts.";
}

function dismissRewrite() {
  document.getElementById("clarify-result").classList.add("hidden");
  _currentClarificationId = null;
  _currentBulletTarget = null;
  _resetClarifyAcceptButton();
}

async function _previewUpdate(draftId, payload) {
  const response = await fetch(`/drafts/${draftId}/preview/update`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = "Preview update failed.";
    try {
      const data = await response.json();
      message = data.detail || message;
    } catch (_error) {
      message = await response.text();
    }
    throw new Error(message);
  }
  window.location.reload();
}

async function saveSummaryPreview(draftId) {
  const summary = document.getElementById("preview-summary")?.value || "";
  await _previewUpdate(draftId, {action: "summary", professional_summary: summary});
}

async function removePreviewBullet(draftId, section, itemIndex, bulletIndex) {
  await _previewUpdate(draftId, {
    action: "remove_bullet",
    section,
    item_index: itemIndex,
    bullet_index: bulletIndex,
  });
}

async function reorderPreviewItems(draftId, section, fromIndex, toIndex) {
  await _previewUpdate(draftId, {
    action: "reorder_item",
    section,
    from_index: fromIndex,
    to_index: toIndex,
  });
}

async function confirmPreviewItem(draftId, itemId) {
  await _previewUpdate(draftId, {action: "confirm_item", item_id: itemId});
}

async function rejectPreviewItem(draftId, itemId) {
  await _previewUpdate(draftId, {action: "reject_item", item_id: itemId});
}

async function saveToProfileMemory(btn, gapLabel, evidence, draftId) {
  btn.disabled = true;
  btn.textContent = "Saving...";
  try {
    const response = await fetch("/verified-facts", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({gap_label: gapLabel, evidence, source_draft_id: draftId}),
    });
    if (response.ok) {
      btn.textContent = "Saved ✓";
      btn.className = btn.className.replace("border-indigo-300 text-indigo-600", "border-green-300 text-green-700");
      btn.classList.add("cursor-default");
    } else {
      btn.textContent = "Error - try again";
      btn.disabled = false;
    }
  } catch (_error) {
    btn.textContent = "Error - try again";
    btn.disabled = false;
  }
}
