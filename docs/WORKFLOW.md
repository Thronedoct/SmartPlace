# Development Workflow

## Branches

- `main`: stable deliverable branch.
- `dev`: integration branch.
- `feature/model-*`: model code and experiments.
- `feature/backend-*`: cloud service and API work.
- `feature/android-*`: Android app work.
- `feature/docs-*`: report, slides, and documentation.

## Daily Collaboration Rule

Each sync should answer four questions:

1. What changed since last sync?
2. What can another member run or review?
3. What is blocked?
4. Does the API contract need to change?

If the API changes, update `docs/API.md` before changing Android or backend code.

## Merge Rule

Before merging into `dev`:

- The code builds or the script starts locally.
- The changed behavior is documented.
- At least one other member has reviewed the affected interface.

Before merging into `main`:

- Android can complete the main flow.
- Backend logs show the request and response.
- The README contains the current run steps.

## Report Ownership

- Member A owns model sections.
- Member B owns architecture, API, deployment, and model-call evidence.
- Member C owns app interaction, screenshots, demo video, and final integration.

Each member writes the first draft for their own part. Member C can do final formatting, but content accuracy remains with the owner.
