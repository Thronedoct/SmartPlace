export function analyzeConfidence(responsePayload) {
  if (!responsePayload || !responsePayload.candidates.length) {
    return {
      tier: "neutral",
      label: "待运行",
      items: ["运行推荐后显示分数饱和、候选重叠和低可信提示。"],
      metrics: {},
    };
  }

  const candidates = responsePayload.candidates;
  const top = candidates[0];
  const second = candidates[1];
  const top3 = candidates.slice(0, 3);
  const topGap = second ? top.score - second.score : top.score;
  const saturatedCount = top3.filter((candidate) => candidate.score >= 0.995).length;
  const maxIou = maxCandidateIou(top3);
  const items = [];

  if (top.score < 0.45) {
    items.push("Top 1 分数低于不推荐阈值，本次结果应作为拒绝或重新取图处理。");
  }
  if (saturatedCount >= 2) {
    items.push("Top 3 中多个候选接近 1.0，存在分数饱和，需要人工复查排序差异。");
  }
  if (topGap < 0.05 && candidates.length > 1) {
    items.push("Top 1 与 Top 2 分差小于 0.05，首选位置不够唯一。");
  }
  if (maxIou >= 0.75) {
    items.push("Top 3 候选框重叠较高，建议启用 IoU 去重或人工选择更多样的位置。");
  }
  if (top.score >= 0.75 && items.length === 0) {
    items.push("Top 1 分数高、候选差异清晰，可作为高可信推荐展示。");
  }
  if (items.length === 0) {
    items.push("结果可用，但建议结合画面语义做一次人工复查。");
  }

  let tier = "review";
  let label = "需要复查";
  if (top.score < 0.45) {
    tier = "low";
    label = "低可信";
  } else if (items.length === 1 && top.score >= 0.75 && saturatedCount < 2 && maxIou < 0.75) {
    tier = "high";
    label = "高可信";
  }

  return {
    tier,
    label,
    items,
    metrics: {
      top_score: round4(top.score),
      top_gap: round4(topGap),
      saturated_top3: saturatedCount,
      max_top3_iou: round4(maxIou),
    },
  };
}

function maxCandidateIou(candidates) {
  let maxIou = 0;
  for (let i = 0; i < candidates.length; i += 1) {
    for (let j = i + 1; j < candidates.length; j += 1) {
      maxIou = Math.max(maxIou, candidateIou(candidates[i], candidates[j]));
    }
  }
  return maxIou;
}

function candidateIou(a, b) {
  const ax2 = a.x + a.w;
  const ay2 = a.y + a.h;
  const bx2 = b.x + b.w;
  const by2 = b.y + b.h;
  const overlapWidth = Math.max(0, Math.min(ax2, bx2) - Math.max(a.x, b.x));
  const overlapHeight = Math.max(0, Math.min(ay2, by2) - Math.max(a.y, b.y));
  const intersection = overlapWidth * overlapHeight;
  if (intersection <= 0) return 0;
  const union = a.w * a.h + b.w * b.h - intersection;
  return union > 0 ? intersection / union : 0;
}

function round4(value) {
  return Math.round(value * 10000) / 10000;
}
