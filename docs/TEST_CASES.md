# Test Case Log

Use this table for all validation cases. Keep screenshots or source images under `assets/` or `report/`.

| ID | Background type | Foreground object | Candidate type | Model version | Score | System rank | Human judgment | Result | Notes |
|---|---|---|---|---|---:|---:|---|---|---|
| T001 | desktop | cup | reasonable support | mock-v0 | 0.86 | 1 | reasonable | pass | Phase-0 placeholder. |
| T002 | floor | chair | scale too large | mock-v0 | 0.61 | 2 | acceptable | review | Phase-0 placeholder. |
| T003 | wall | plant | floating / unsupported | mock-v0 | 0.28 | 3 | unreasonable | fail | Phase-0 placeholder. |

## Required Coverage

Final project should include at least 18 cases:

- Desktop/tabletop scenes.
- Floor scenes.
- Wall/shelf scenes.
- Outdoor scenes.
- Clearly reasonable positions.
- Clearly wrong positions.
- Boundary overflow or unreasonable scale cases.

## Per-case Evidence

For important cases, save:

- Original background.
- Foreground object.
- Top-3 candidate screenshot.
- Model score table.
- Human judgment.
- Failure reason if the model result is poor.
