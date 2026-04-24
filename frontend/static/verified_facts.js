async function deactivateFact(factId) {
  if (!confirm("Remove this fact from profile memory? It will no longer appear in new CV drafts.")) {
    return;
  }
  const response = await fetch("/verified-facts/" + factId, {method: "DELETE"});
  if (response.ok || response.status === 204) {
    document.getElementById("fact-" + factId)?.remove();
  }
}
