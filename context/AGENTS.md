# Project Context

This repository is a sports first Vision Analytics platform. The goal is to provide a job based pipeline that turns video into tracks, events, metrics, and exports while keeping a profile system that makes it reusable for other domains.

## Key principles
- Sports first UX with clear overlays, timelines, and coach friendly outputs
- Pipeline is deterministic and explainable with events that state why they fired
- Artifacts are stored per job with a manifest and reproducible configs

## Development notes
- API is FastAPI and stores artifacts under `data/jobs/<job_id>`
- UI expects the API at `VITE_API_URL` and uses polling for job status
- Keep the shared data schema consistent between API outputs and UI readers
