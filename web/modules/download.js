export function exportRecommendation(format, { responsePayload, activeDemoCase, confidence }) {
  if (!responsePayload) return;
  const baseName = responsePayload.request_id || "smartplace-result";
  if (format === "json") {
    const payload = {
      exported_at: new Date().toISOString(),
      demo_case: activeDemoCase,
      confidence: confidence || null,
      recommendation: responsePayload,
    };
    downloadBlob(
      `${baseName}.json`,
      JSON.stringify(payload, null, 2),
      "application/json",
    );
    return;
  }

  const candidates = Array.isArray(responsePayload.candidates) ? responsePayload.candidates : [];
  const rows = candidates.map((candidate) => ({
    request_id: responsePayload.request_id,
    model_version: responsePayload.model_version,
    runtime_ms: responsePayload.runtime_ms,
    confidence_label: confidence?.label || "",
    rank: candidate.rank,
    score: candidate.score,
    tier: candidate.tier,
    label: candidate.label,
    x: candidate.x,
    y: candidate.y,
    w: candidate.w,
    h: candidate.h,
    reason: candidate.reason,
  }));
  downloadBlob(`${baseName}.csv`, toCsv(rows), "text/csv;charset=utf-8");
}

function toCsv(rows) {
  if (!rows.length) return "";
  const headers = Object.keys(rows[0]);
  const lines = [headers.join(",")];
  rows.forEach((row) => {
    lines.push(headers.map((key) => csvEscape(row[key])).join(","));
  });
  return lines.join("\n");
}

function csvEscape(value) {
  const text = String(value ?? "");
  if (/[",\r\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function downloadBlob(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
