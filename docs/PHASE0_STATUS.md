# Phase 0 Status

## Done

- Course Android demo inspected and kept as `OPAAndroidDemoSimp/`.
- Root documentation scaffold added.
- API contract added.
- Collaboration workflow added.
- Test case template added.
- Model plan added.
- Git repository initialized on `main`.
- Mock FastAPI service added.
- Dependency-free standard-library mock service added and locally verified.

## Current Decision

Use the course Android demo as the initial app skeleton, but do not bind the whole project to it. The backend API is kept independent so the team can later replace the Android app or rewrite screens without changing the model service contract.

## Next Steps

1. Member B runs the mock backend.
2. Member C points Android networking code to `/api/place/recommend`.
3. Member A runs the first real OPA/libcom reference example and records input/output.
4. The team confirms whether the response fields in `docs/API.md` are enough for the first Android integration.
