# API Reference

Base URL: `http://localhost:8000`

## Auth
If `VAP_API_KEY` is set on the API, include `X-API-Key: <key>` or `?api_key=<key>` for SSE endpoints.

## Health
- `GET /api/health`

## Jobs
- `POST /api/jobs` multipart form with `video` or `image` and optional `config` JSON
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/config`
- `PATCH /api/jobs/{job_id}/config`
- `POST /api/jobs/{job_id}/rerun`

## Streams
- `POST /api/streams`
  ```json
  {
    "stream_url": "https://example.com/stream.m3u8",
    "config": {"profile": "soccer", "analytics_enabled": true}
  }
  ```

## Artifacts
- `GET /api/jobs/{job_id}/tracks`
- `GET /api/jobs/{job_id}/metrics`
- `GET /api/jobs/{job_id}/events`
- `GET /api/jobs/{job_id}/manifest`
- `GET /api/jobs/{job_id}/artifacts/{artifact_name}`

## Share links
- `POST /api/jobs/{job_id}/share?ttl_hours=168`
- `GET /api/share/{share_id}/job`
- `GET /api/share/{share_id}/tracks`
- `GET /api/share/{share_id}/metrics`
- `GET /api/share/{share_id}/events`
- `GET /api/share/{share_id}/input`

## Live updates (SSE)
- `GET /api/updates/jobs`
- `GET /api/updates/jobs/{job_id}`

## Example
Create a job
```
curl -X POST http://localhost:8000/api/jobs \
  -H "X-API-Key: $VAP_API_KEY" \
  -F "video=@sample.mp4" \
  -F 'config={"profile":"soccer"}'
```
