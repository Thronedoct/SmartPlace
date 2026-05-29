# SmartPlace

SmartPlace is the course project for direction A: intelligent object placement and composition quality assessment.

The planned product is an Android app that lets a user choose a background image and a foreground object, sends them to a cloud inference service, and receives ranked placement recommendations with scores and visual evidence.

## Current Phase

Phase 0 is the collaboration and mock-demo phase:

- Keep `OPAAndroidDemoSimp/` as the course Android reference skeleton.
- Use `server/` for the cloud inference service.
- Use `docs/API.md` as the front-end/back-end contract.
- Use mock recommendation data first, then replace it with real OPA/libcom inference.

## Repository Layout

```text
SmartPlace/
├── OPAAndroidDemoSimp/      # Course Android demo skeleton
├── server/                  # FastAPI cloud inference service
├── docs/                    # API, workflow, model plan, test records
├── assets/                  # Shared test images and materials
├── report/                  # Report, slides, screenshots, videos
└── README.md
```

## Phase 0 Quick Start

Run the dependency-free mock backend first:

```bash
python server/mock_stdlib.py --host 0.0.0.0 --port 8000
```

Or run the FastAPI mock backend after installing dependencies:

```bash
cd server
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Check the mock API:

```bash
curl http://127.0.0.1:8000/api/health
```

The Android app should call:

```text
POST http://<server-ip>:8000/api/place/recommend
```

For an Android emulator, use `http://10.0.2.2:8000`. For a physical phone, use the computer's LAN IP.

## Team Roles

- Member A: model adaptation and model experiments.
- Member B: cloud inference service and recommendation pipeline.
- Member C: Android app, interaction, demo video, and final material integration.

Each member owns both implementation and the corresponding report/PPT section.
