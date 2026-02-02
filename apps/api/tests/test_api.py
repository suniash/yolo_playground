from __future__ import annotations

import json
import time
from fastapi.testclient import TestClient

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_job_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("VAP_DATA_DIR", str(tmp_path))
    with TestClient(app) as local_client:
        response = local_client.post(
            "/api/jobs",
            files={"video": ("clip.mp4", b"fake", "video/mp4")},
            data={"config": json.dumps({"profile": "soccer", "analytics_enabled": True})},
        )
        assert response.status_code == 200
        job = response.json()
        job_id = job["id"]

        job_response = local_client.get(f"/api/jobs/{job_id}")
        assert job_response.status_code == 200

        deadline = time.time() + 10
        job_state = None
        while time.time() < deadline:
            job_state = local_client.get(f"/api/jobs/{job_id}").json()
            if job_state.get("status") == "completed":
                break
            time.sleep(0.2)
        assert job_state and job_state.get("status") == "completed"

        config_response = local_client.get(f"/api/jobs/{job_id}/config")
        assert config_response.status_code == 200

        update_response = local_client.patch(
            f"/api/jobs/{job_id}/config",
            json={"zones": [{"id": "zone-1", "name": "Box", "polygon": [[0, 0], [1, 0], [1, 1]]}]},
        )
        assert update_response.status_code == 200

        rerun_response = local_client.post(f"/api/jobs/{job_id}/rerun", json={"team_overrides": {"p1": "A"}})
        assert rerun_response.status_code == 200
