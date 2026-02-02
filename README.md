# Vision Analytics Platform

A sports first vision analytics workbench that turns video into track data, events, and coaching metrics. Upload a clip, run the pipeline, review overlays, and export results. The pipeline is profile driven so the same backbone can support traffic, retail, or warehouse use cases later.

## What is included
- Job based processing with status, progress, and artifact storage
- CV pipeline scaffolding with detection, tracking, analytics, and events
- Results studio with overlays, timeline, metrics, and exports
- Sport profiles for soccer and basketball

## Quick start
API
Use Python 3.12 for the API venv on macOS to avoid build issues with pydantic-core.
1. `cd apps/api`
2. `python -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. `uvicorn app.main:app --reload --port 8000`

Optional real CV
1. `pip install -r requirements-cv.txt`
2. `VAP_CV_PROVIDER=ultralytics VAP_MODEL=yolov8n.pt uvicorn app.main:app --reload --port 8000`

Web
1. `cd apps/web`
2. `npm install`
3. `npm run dev`

Set `VITE_API_URL` if your API runs on a different host.
If `VAP_API_KEY` is set on the API, set `VITE_API_KEY` in the web app to match.

## Repository layout
- `apps/api` FastAPI service and pipeline core
- `apps/web` React studio UI
- `context` project context and planning docs
- `data` job artifacts and exports
