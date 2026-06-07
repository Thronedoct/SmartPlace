export async function fetchHealth() {
  const response = await fetch("/api/health");
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export async function fetchDemoCases() {
  const response = await fetch("/api/demo/cases");
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export async function requestRecommendation({
  backgroundFile,
  foregroundFile,
  maskFile,
  candidateCount,
  foregroundScale,
  mode,
}) {
  const data = new FormData();
  data.append("background", backgroundFile);
  data.append("foreground", foregroundFile);
  if (maskFile) data.append("mask", maskFile);
  data.append("candidate_count", candidateCount);
  data.append("foreground_scale", foregroundScale);
  data.append("mode", mode);

  const response = await fetch("/api/place/recommend", {
    method: "POST",
    body: data,
  });
  if (!response.ok) {
    throw new Error(await buildErrorMessage(response));
  }
  return response.json();
}

export async function fileFromUrl(url, filename) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url} HTTP ${response.status}`);
  const blob = await response.blob();
  return new File([blob], filename, { type: blob.type || "image/jpeg" });
}

async function buildErrorMessage(response) {
  try {
    const payload = await response.json();
    if (payload.detail) return `HTTP ${response.status}: ${payload.detail}`;
  } catch (error) {
    // Fall through to the compact HTTP status message.
  }
  return `HTTP ${response.status}`;
}
