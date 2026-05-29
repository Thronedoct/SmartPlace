# Model Plan

## Direction

Use direction A: intelligent object placement and composition quality assessment.

Primary model candidates:

- OPA/Object Placement Assessment model.
- libcom object placement quality assessment components.
- TopNet as optional reference for candidate placement.

## Phase-0 Mock Output

Before real model integration, the backend returns fixed candidates with the same structure as the future model response.

The mock response is intentionally shaped like the final API:

- Top-3 placement boxes.
- 0-1 score.
- Three-tier label.
- Runtime and model version.

## Required Model Work

The standard three-person team needs at least two model-related works, including at least one body-level model modification.

Planned body-level modification:

- Change scoring input from RGB composite image to RGB + foreground mask.
- Compare the original RGB model and the RGB+mask model on at least 6 candidate groups.

Planned functional modification:

- Generate multiple placement candidates.
- Score each candidate.
- Sort candidates and return Top 3 recommendations.

## Evidence to Collect

- Reference model run screenshot.
- Weight loading code path.
- Input tensor shape before and after modification.
- Inference log for a fresh image.
- Ranking comparison table.
- Runtime comparison table.
- Success and failure cases.
- Grad-CAM, occlusion, or other explanation output.
