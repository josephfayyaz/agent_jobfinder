/*
 * Draft detail controller.
 *
 * The page uses inline buttons in the server-rendered template, so these
 * actions are intentionally exposed on `window`. Keep internal state local to
 * this file so future UI work can replace the inline handlers without changing
 * the backend routes.
 */

const draftClarifyState = {
  clarificationId: null,
  bulletTarget: null,
};

function clarifyElements() {
  return {
    acceptButton: document.getElementById("clarify-accept-btn"),
    promoteButton: document.getElementById("clarify-promote-btn"),
    status: document.getElementById("clarify-status"),
    loading: document.getElementById("clarify-loading"),
    result: document.getElementById("clarify-result"),
    original: document.getElementById("clarify-original"),
    rewrite: document.getElementById("clarify-rewrite"),
    panel: document.getElementById("bullet-clarify-panel"),
  };
}

function resetClarifyButtons() {
  const els = clarifyElements();
  if (els.acceptButton) {
    els.acceptButton.textContent = "Apply to Draft";
    els.acceptButton.disabled = false;
  }
  if (els.promoteButton) {
    els.promoteButton.textContent = "Save for Future Drafts";
    els.promoteButton.disabled = true;
  }
  if (els.status) {
    els.status.textContent = "";
  }
}

async function previewUpdate(draftId, payload) {
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

async function rewriteBullet(btn, draftId, bullet, targetSection, targetItemIndex, targetBulletIndex) {
  const els = clarifyElements();
  draftClarifyState.clarificationId = null;
  draftClarifyState.bulletTarget = btn.parentElement.querySelector("span");
  resetClarifyButtons();

  if (els.original) {
    els.original.textContent = bullet;
  }
  if (els.rewrite) {
    els.rewrite.textContent = "";
  }
  els.loading?.classList.remove("hidden");
  els.result?.classList.add("hidden");
  els.panel?.scrollIntoView({behavior: "smooth", block: "nearest"});

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
    draftClarifyState.clarificationId = data.id;
    if (els.rewrite) {
      els.rewrite.textContent = data.suggested_rewrite;
    }
  } catch (err) {
    if (els.rewrite) {
      els.rewrite.textContent = `Error: ${err.message}`;
    }
    if (els.acceptButton) {
      els.acceptButton.disabled = true;
    }
  } finally {
    els.loading?.classList.add("hidden");
    els.result?.classList.remove("hidden");
  }
}

async function acceptRewrite() {
  if (!draftClarifyState.clarificationId) {
    return;
  }
  const els = clarifyElements();
  const response = await fetch(
    `/drafts/clarifications/${draftClarifyState.clarificationId}/accept`,
    {method: "POST"}
  );
  if (!response.ok) {
    if (els.acceptButton) {
      els.acceptButton.textContent = "Apply failed";
    }
    return;
  }
  const rewritten = els.rewrite?.textContent || "";
  if (draftClarifyState.bulletTarget) {
    draftClarifyState.bulletTarget.textContent = rewritten;
  }
  if (els.acceptButton) {
    els.acceptButton.textContent = "✓ Applied";
    els.acceptButton.disabled = true;
  }
  if (els.promoteButton) {
    els.promoteButton.disabled = false;
  }
  if (els.status) {
    els.status.textContent = "Draft updated. The rendered artifact was refreshed in the background.";
  }
}

async function promoteRewrite() {
  if (!draftClarifyState.clarificationId) {
    return;
  }
  const els = clarifyElements();
  const response = await fetch(
    `/drafts/clarifications/${draftClarifyState.clarificationId}/promote`,
    {method: "POST"}
  );
  if (!response.ok) {
    if (els.status) {
      els.status.textContent = "Could not save for future drafts.";
    }
    return;
  }
  if (els.promoteButton) {
    els.promoteButton.textContent = "✓ Saved for Future";
    els.promoteButton.disabled = true;
  }
  if (els.status) {
    els.status.textContent =
      "This approved wording is now saved in your role-specific fact sheet bank for future drafts.";
  }
}

function dismissRewrite() {
  clarifyElements().result?.classList.add("hidden");
  draftClarifyState.clarificationId = null;
  draftClarifyState.bulletTarget = null;
  resetClarifyButtons();
}

async function saveSummaryPreview(draftId) {
  const summary = document.getElementById("preview-summary")?.value || "";
  await previewUpdate(draftId, {action: "summary", professional_summary: summary});
}

async function removePreviewBullet(draftId, section, itemIndex, bulletIndex) {
  await previewUpdate(draftId, {
    action: "remove_bullet",
    section,
    item_index: itemIndex,
    bullet_index: bulletIndex,
  });
}

async function reorderPreviewItems(draftId, section, fromIndex, toIndex) {
  await previewUpdate(draftId, {
    action: "reorder_item",
    section,
    from_index: fromIndex,
    to_index: toIndex,
  });
}

async function confirmPreviewItem(draftId, itemId) {
  await previewUpdate(draftId, {action: "confirm_item", item_id: itemId});
}

async function rejectPreviewItem(draftId, itemId) {
  await previewUpdate(draftId, {action: "reject_item", item_id: itemId});
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

window.rewriteBullet = rewriteBullet;
window.acceptRewrite = acceptRewrite;
window.promoteRewrite = promoteRewrite;
window.dismissRewrite = dismissRewrite;
window.saveSummaryPreview = saveSummaryPreview;
window.removePreviewBullet = removePreviewBullet;
window.reorderPreviewItems = reorderPreviewItems;
window.confirmPreviewItem = confirmPreviewItem;
window.rejectPreviewItem = rejectPreviewItem;
window.saveToProfileMemory = saveToProfileMemory;
