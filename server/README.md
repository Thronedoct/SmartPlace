# SmartPlace Mock Backend

This is the phase-0 cloud inference mock service.

It returns fixed Top-3 placement recommendations with the same response shape planned for the real OPA/libcom model.

## Run Without Extra Dependencies

Use this for the phase-0 Android connectivity demo:

```bash
python mock_stdlib.py --host 0.0.0.0 --port 8000
```

## Run FastAPI Version

```bash
cd server
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /api/health`
- `POST /api/place/recommend`

See `../docs/API.md` for request and response details.

## Android URLs

- Emulator: `http://10.0.2.2:8000`
- Physical phone: `http://<computer-lan-ip>:8000`
