from __future__ import annotations

import asyncio
import csv
import math
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable

from .config import CV_PROVIDER, DEFAULT_PROFILE, FIELD_DIMENSIONS
from .cv import run_ultralytics
from .schemas import ArtifactItem, ArtifactManifest, JobConfig, JobRecord, JobStatus
from .storage import artifacts_dir, exports_dir, file_size, save_json


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def _field_dims(profile: str) -> tuple[float, float]:
    dims = FIELD_DIMENSIONS.get(profile, FIELD_DIMENSIONS[DEFAULT_PROFILE])
    return dims["length"], dims["width"]


def _map_to_field(x: float, y: float, width: float, height: float, profile: str) -> tuple[float, float]:
    length, field_width = _field_dims(profile)
    return (x / width) * length, (y / height) * field_width


def _generate_tracks(config: JobConfig, seed: int) -> tuple[dict[str, Any], dict[str, Any]]:
    rng = random.Random(seed)
    profile = config.profile.value
    width = 1280
    height = 720
    fps = 25
    frame_count = 250
    player_count = 20 if profile == "soccer" else 10
    player_size = (32, 64) if profile == "soccer" else (36, 72)

    players = []
    for idx in range(player_count):
        team = "A" if idx < player_count / 2 else "B"
        x = rng.uniform(200, width - 200)
        y = rng.uniform(100, height - 100)
        vx = rng.uniform(-2.5, 2.5)
        vy = rng.uniform(-2.0, 2.0)
        players.append({
            "id": f"p{idx + 1}",
            "team": team,
            "x": x,
            "y": y,
            "vx": vx,
            "vy": vy,
        })

    ball_owner = rng.choice(players)["id"]
    possession_timer = 0

    frames = []
    positions_by_player: dict[str, list[tuple[float, float]]] = {p["id"]: [] for p in players}
    ball_positions: list[tuple[float, float]] = []
    owner_by_frame: list[str] = []

    for frame in range(frame_count):
        objects = []
        for player in players:
            player["x"] += player["vx"] + rng.uniform(-0.6, 0.6)
            player["y"] += player["vy"] + rng.uniform(-0.5, 0.5)
            player["x"] = _clamp(player["x"], 60, width - 60)
            player["y"] = _clamp(player["y"], 60, height - 60)

            bbox_w, bbox_h = player_size
            bbox = [
                round(player["x"] - bbox_w / 2, 2),
                round(player["y"] - bbox_h / 2, 2),
                bbox_w,
                bbox_h,
            ]
            objects.append({
                "id": player["id"],
                "label": "player",
                "team": player["team"],
                "bbox": bbox,
                "confidence": round(rng.uniform(0.82, 0.98), 3),
            })
            positions_by_player[player["id"]].append((player["x"], player["y"]))

        possession_timer += 1
        if possession_timer > rng.randint(20, 45):
            ball_owner = rng.choice(players)["id"]
            possession_timer = 0

        owner_by_frame.append(ball_owner)
        owner = next(p for p in players if p["id"] == ball_owner)
        ball_x = owner["x"] + rng.uniform(-18, 18)
        ball_y = owner["y"] + rng.uniform(-18, 18)
        ball_positions.append((ball_x, ball_y))
        objects.append({
            "id": "ball",
            "label": "ball",
            "team": None,
            "bbox": [round(ball_x - 8, 2), round(ball_y - 8, 2), 16, 16],
            "confidence": round(rng.uniform(0.7, 0.95), 3),
        })

        frames.append({"frame": frame, "objects": objects})

    tracks_data = {
        "meta": {
            "profile": profile,
            "fps": fps,
            "frame_count": frame_count,
            "width": width,
            "height": height,
        },
        "tracks": [
            {"id": p["id"], "label": "player", "team": p["team"]} for p in players
        ],
        "frames": frames,
    }

    series = {
        "player_positions": positions_by_player,
        "ball_positions": ball_positions,
        "owner_by_frame": owner_by_frame,
        "fps": fps,
        "width": width,
        "height": height,
    }

    return tracks_data, series


def _compute_metrics(config: JobConfig, series: dict[str, Any]) -> dict[str, Any]:
    profile = config.profile.value
    fps = series["fps"]
    width = series["width"]
    height = series["height"]
    player_positions: dict[str, list[tuple[float, float]]] = series["player_positions"]
    ball_positions: list[tuple[float, float]] = series["ball_positions"]
    owner_by_frame: list[str] = series["owner_by_frame"]

    def _default_team(player_id: str) -> str:
        if player_id.startswith("p"):
            try:
                return "A" if int(player_id[1:]) <= len(player_positions) / 2 else "B"
            except ValueError:
                return "A"
        return "A"

    def _resolve_team(player_id: str) -> str:
        override = config.team_overrides.get(player_id)
        if override in {"A", "B"}:
            return override
        return _default_team(player_id)

    team_possession_frames = {"A": 0, "B": 0}
    for owner in owner_by_frame:
        team = _resolve_team(owner)
        team_possession_frames[team] += 1

    frame_count = len(owner_by_frame)
    team_possession = {
        team: round(count / frame_count, 3) for team, count in team_possession_frames.items()
    }

    length, field_width = _field_dims(profile)

    player_metrics = []
    heatmap_grid = {"A": [[0 for _ in range(10)] for _ in range(6)], "B": [[0 for _ in range(10)] for _ in range(6)]}
    player_heatmaps: dict[str, list[list[int]]] = {}

    for player_id, positions in player_positions.items():
        total_distance = 0.0
        speeds = []
        heatmap = [[0 for _ in range(10)] for _ in range(6)]
        last_field_pos = None
        for (x, y) in positions:
            field_x, field_y = _map_to_field(x, y, width, height, profile)
            if last_field_pos is not None:
                dx = field_x - last_field_pos[0]
                dy = field_y - last_field_pos[1]
                dist = math.hypot(dx, dy)
                total_distance += dist
                speeds.append(dist * fps)
            last_field_pos = (field_x, field_y)

            cell_x = int(_clamp((field_x / length) * 10, 0, 9))
            cell_y = int(_clamp((field_y / field_width) * 6, 0, 5))
            heatmap[cell_y][cell_x] += 1

        team = _resolve_team(player_id)
        for row_idx in range(6):
            for col_idx in range(10):
                heatmap_grid[team][row_idx][col_idx] += heatmap[row_idx][col_idx]

        player_heatmaps[player_id] = heatmap
        avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
        player_metrics.append({
            "id": player_id,
            "team": team,
            "distance_m": round(total_distance, 2),
            "avg_speed_mps": round(avg_speed, 2),
            "max_speed_mps": round(max(speeds) if speeds else 0.0, 2),
        })

    ball_path = [
        {
            "frame": idx,
            "image_x": round(pos[0], 2),
            "image_y": round(pos[1], 2),
            "field_x": round(_map_to_field(pos[0], pos[1], width, height, profile)[0], 2),
            "field_y": round(_map_to_field(pos[0], pos[1], width, height, profile)[1], 2),
        }
        for idx, pos in enumerate(ball_positions)
    ]

    metrics = {
        "summary": {
            "player_count": len(player_positions),
            "team_possession": team_possession,
            "avg_speed_mps": round(sum(p["avg_speed_mps"] for p in player_metrics) / len(player_metrics), 2),
        },
        "players": player_metrics,
        "heatmaps": {
            "teams": heatmap_grid,
            "players": player_heatmaps,
        },
        "ball_trajectory": ball_path,
    }

    return metrics


def _compute_events(config: JobConfig, series: dict[str, Any]) -> list[dict[str, Any]]:
    profile = config.profile.value
    fps = series["fps"]
    width = series["width"]
    height = series["height"]
    ball_positions: list[tuple[float, float]] = series["ball_positions"]
    owner_by_frame: list[str] = series["owner_by_frame"]
    player_positions: dict[str, list[tuple[float, float]]] = series["player_positions"]

    events = []

    possession_min_frames = int(config.thresholds.get("possession_min_frames", 8))
    sprint_speed = float(
        config.thresholds.get("sprint_speed_mps", 6.0 if profile == "soccer" else 5.0)
    )
    sprint_min_frames = int(config.thresholds.get("sprint_min_frames", 6))
    crowding_distance = float(config.thresholds.get("crowding_distance_px", 80))
    crowding_player_count = int(config.thresholds.get("crowding_player_count", 6))
    crowding_min_frames = int(config.thresholds.get("crowding_min_frames", 5))
    zone_entry_min_frames = int(config.thresholds.get("zone_entry_min_frames", 4))

    def _point_in_polygon(x: float, y: float, polygon: list[list[float]]) -> bool:
        inside = False
        if len(polygon) < 3:
            return False
        j = len(polygon) - 1
        for i in range(len(polygon)):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            intersects = ((yi > y) != (yj > y)) and (
                x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi
            )
            if intersects:
                inside = not inside
            j = i
        return inside

    last_owner = owner_by_frame[0]
    stable_count = 0
    for idx, owner in enumerate(owner_by_frame):
        if owner == last_owner:
            stable_count += 1
        else:
            if stable_count >= possession_min_frames:
                events.append({
                    "id": f"evt_pos_{idx}",
                    "type": "possession_change",
                    "start": round(idx / fps, 2),
                    "end": round((idx + 4) / fps, 2),
                    "frame": idx,
                    "involved": [last_owner, owner],
                    "confidence": 0.78,
                    "explanation": (
                        f"ball owner changed from {last_owner} to {owner} and held for {stable_count} frames"
                    ),
                })
            last_owner = owner
            stable_count = 0

    length, field_width = _field_dims(profile)
    zone_threshold = length * 0.66
    shot_threshold = length * 0.92

    if config.zones:
        zone_state = {
            zone.id: {"inside": False, "streak": 0} for zone in config.zones
        }
        shot_keywords = ("shot", "box", "key", "paint")

        for idx, (x, y) in enumerate(ball_positions):
            for zone in config.zones:
                state = zone_state[zone.id]
                inside = _point_in_polygon(x, y, zone.polygon)
                if inside and not state["inside"]:
                    state["streak"] += 1
                    if state["streak"] >= zone_entry_min_frames:
                        event_base = {
                            "id": f"evt_zone_{zone.id}_{idx}",
                            "start": round((idx - state["streak"] + 1) / fps, 2),
                            "end": round((idx + 6) / fps, 2),
                            "frame": idx,
                            "involved": [owner_by_frame[idx]],
                            "confidence": 0.66,
                            "zone_id": zone.id,
                            "zone_name": zone.name,
                            "explanation": (
                                f"ball entered {zone.name} for {state['streak']} frames"
                            ),
                        }
                        events.append({**event_base, "type": "entry_into_zone"})
                        if any(keyword in zone.name.lower() for keyword in shot_keywords):
                            events.append({
                                **event_base,
                                "id": f"evt_shot_{zone.id}_{idx}",
                                "type": "shot_attempt",
                                "confidence": 0.72,
                                "explanation": f"ball entered shot zone {zone.name}",
                            })
                        state["inside"] = True
                elif inside and state["inside"]:
                    continue
                else:
                    state["streak"] = 0
                    state["inside"] = False
    else:
        for idx, (x, y) in enumerate(ball_positions):
            field_x, field_y = _map_to_field(x, y, width, height, profile)
            if field_x > zone_threshold and idx % 40 == 0:
                events.append({
                    "id": f"evt_zone_{idx}",
                    "type": "entry_into_zone",
                    "start": round(idx / fps, 2),
                    "end": round((idx + 10) / fps, 2),
                    "frame": idx,
                    "involved": [owner_by_frame[idx]],
                    "confidence": 0.64,
                    "explanation": "ball entered attacking third",
                })
            if field_x > shot_threshold and idx % 50 == 0:
                events.append({
                    "id": f"evt_shot_{idx}",
                    "type": "shot_attempt",
                    "start": round(idx / fps, 2),
                    "end": round((idx + 6) / fps, 2),
                    "frame": idx,
                    "involved": [owner_by_frame[idx]],
                    "confidence": 0.7,
                    "explanation": "ball reached shot zone",
                })

    for player_id, positions in player_positions.items():
        speed_streak = 0
        last_pos = None
        for idx, (x, y) in enumerate(positions):
            field_x, field_y = _map_to_field(x, y, width, height, profile)
            if last_pos is not None:
                dist = math.hypot(field_x - last_pos[0], field_y - last_pos[1])
                speed = dist * fps
                if speed > sprint_speed:
                    speed_streak += 1
                else:
                    if speed_streak >= sprint_min_frames:
                        events.append({
                            "id": f"evt_sprint_{player_id}_{idx}",
                            "type": "sprint_burst",
                            "start": round((idx - speed_streak) / fps, 2),
                            "end": round(idx / fps, 2),
                            "frame": idx,
                            "involved": [player_id],
                            "confidence": 0.6,
                            "explanation": f"player exceeded sprint threshold for {speed_streak} frames",
                        })
                    speed_streak = 0
            last_pos = (field_x, field_y)

    crowding_window = 0
    for idx, (ball_x, ball_y) in enumerate(ball_positions):
        nearby = 0
        for positions in player_positions.values():
            px, py = positions[idx]
            if math.hypot(px - ball_x, py - ball_y) < crowding_distance:
                nearby += 1
        if nearby >= crowding_player_count:
            crowding_window += 1
            if crowding_window == crowding_min_frames:
                events.append({
                    "id": f"evt_crowd_{idx}",
                    "type": "crowding",
                    "start": round((idx - crowding_min_frames) / fps, 2),
                    "end": round(idx / fps, 2),
                    "frame": idx,
                    "involved": [owner_by_frame[idx]],
                    "confidence": 0.58,
                    "explanation": f"{nearby} players clustered near ball",
                })
        else:
            crowding_window = 0

    events.sort(key=lambda item: item["start"])
    return events


def _write_exports(job_id: str, events: list[dict[str, Any]], metrics: dict[str, Any]) -> list[ArtifactItem]:
    export_dir = exports_dir(job_id)
    events_csv = export_dir / "events.csv"
    summary_csv = export_dir / "summary.csv"
    report_html = export_dir / "report.html"

    with events_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "type", "start", "end", "frame", "confidence", "explanation"])
        writer.writeheader()
        for event in events:
            writer.writerow({
                "id": event["id"],
                "type": event["type"],
                "start": event["start"],
                "end": event["end"],
                "frame": event["frame"],
                "confidence": event["confidence"],
                "explanation": event["explanation"],
            })

    summary_rows = [
        {"metric": "player_count", "value": metrics["summary"]["player_count"]},
        {"metric": "team_a_possession", "value": metrics["summary"]["team_possession"]["A"]},
        {"metric": "team_b_possession", "value": metrics["summary"]["team_possession"]["B"]},
        {"metric": "avg_speed_mps", "value": metrics["summary"]["avg_speed_mps"]},
    ]
    with summary_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(summary_rows)

    report_html.write_text(
        f"""
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Vision Analytics Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; }}
    h1 {{ margin-bottom: 8px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
    .card {{ border: 1px solid #d2d2d2; border-radius: 12px; padding: 16px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td, th {{ padding: 6px 8px; border-bottom: 1px solid #eee; text-align: left; }}
  </style>
</head>
<body>
  <h1>Vision Analytics Report</h1>
  <p>Generated on {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}</p>
  <div class=\"grid\">
    <div class=\"card\">
      <h2>Summary</h2>
      <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Player count</td><td>{metrics["summary"]["player_count"]}</td></tr>
        <tr><td>Team A possession</td><td>{metrics["summary"]["team_possession"]["A"]}</td></tr>
        <tr><td>Team B possession</td><td>{metrics["summary"]["team_possession"]["B"]}</td></tr>
        <tr><td>Average speed (m/s)</td><td>{metrics["summary"]["avg_speed_mps"]}</td></tr>
      </table>
    </div>
    <div class=\"card\">
      <h2>Events</h2>
      <p>{len(events)} detected events</p>
    </div>
  </div>
</body>
</html>
""",
        encoding="utf-8",
    )

    exports = [
        ArtifactItem(name="events_csv", kind="export", path=str(events_csv), content_type="text/csv", size_bytes=file_size(events_csv)),
        ArtifactItem(name="summary_csv", kind="export", path=str(summary_csv), content_type="text/csv", size_bytes=file_size(summary_csv)),
        ArtifactItem(name="report_html", kind="export", path=str(report_html), content_type="text/html", size_bytes=file_size(report_html)),
    ]
    return exports


def recompute_analytics(job_id: str, config: JobConfig, series: dict[str, Any]) -> tuple[list[ArtifactItem], dict[str, Any], list[dict[str, Any]]]:
    artifacts_path = artifacts_dir(job_id)
    metrics = _compute_metrics(config, series)
    events = _compute_events(config, series)
    save_json(artifacts_path / "metrics.json", metrics)
    save_json(artifacts_path / "events.json", {"events": events})

    items = [
        ArtifactItem(
            name="metrics",
            kind="artifact",
            path=str(artifacts_path / "metrics.json"),
            content_type="application/json",
            size_bytes=file_size(artifacts_path / "metrics.json"),
        ),
        ArtifactItem(
            name="events",
            kind="artifact",
            path=str(artifacts_path / "events.json"),
            content_type="application/json",
            size_bytes=file_size(artifacts_path / "events.json"),
        ),
    ]
    items.extend(_write_exports(job_id, events, metrics))
    return items, metrics, events


async def run_pipeline(
    job: JobRecord,
    input_path: Path | None,
    on_update: Callable[[JobRecord], Awaitable[None]] | None = None,
) -> ArtifactManifest:
    stages = [
        ("ingest", 0.1, 0.4),
        ("detect", 0.35, 0.6),
        ("track", 0.55, 0.7),
        ("understand", 0.7, 0.85),
        ("analytics", 0.85, 0.95),
        ("exports", 1.0, 0.4),
    ]

    manifest = ArtifactManifest(items=[])
    artifacts_path = artifacts_dir(job.id)

    for stage, progress, delay in stages:
        job.stage = stage
        job.progress = progress
        job.updated_at = datetime.utcnow()
        if on_update:
            await on_update(job)
        await asyncio.sleep(delay)

        if stage == "detect":
            if input_path and CV_PROVIDER != "synthetic":
                try:
                    tracks_data, series = run_ultralytics(input_path, job.config)
                    job.summary["cv_provider"] = CV_PROVIDER
                except Exception as exc:
                    job.summary["cv_warning"] = str(exc)
                    tracks_data, series = _generate_tracks(job.config, seed=hash(job.id) % 10000)
            else:
                tracks_data, series = _generate_tracks(job.config, seed=hash(job.id) % 10000)
            save_json(artifacts_path / "tracks.json", tracks_data)
            save_json(artifacts_path / "series.json", series)
            manifest.items.append(ArtifactItem(
                name="tracks",
                kind="artifact",
                path=str(artifacts_path / "tracks.json"),
                content_type="application/json",
                size_bytes=file_size(artifacts_path / "tracks.json"),
            ))
            manifest.items.append(ArtifactItem(
                name="series",
                kind="artifact",
                path=str(artifacts_path / "series.json"),
                content_type="application/json",
                size_bytes=file_size(artifacts_path / "series.json"),
            ))
            job.summary["frames"] = tracks_data["meta"]["frame_count"]
            job.summary["fps"] = tracks_data["meta"]["fps"]
            job.summary["profile"] = tracks_data["meta"]["profile"]
            job.summary["series"] = series
            if on_update:
                await on_update(job)

        if stage == "analytics" and job.summary.get("series"):
            series = job.summary["series"]
            metrics = _compute_metrics(job.config, series)
            events = _compute_events(job.config, series)
            save_json(artifacts_path / "metrics.json", metrics)
            save_json(artifacts_path / "events.json", {"events": events})
            manifest.items.append(ArtifactItem(
                name="metrics",
                kind="artifact",
                path=str(artifacts_path / "metrics.json"),
                content_type="application/json",
                size_bytes=file_size(artifacts_path / "metrics.json"),
            ))
            manifest.items.append(ArtifactItem(
                name="events",
                kind="artifact",
                path=str(artifacts_path / "events.json"),
                content_type="application/json",
                size_bytes=file_size(artifacts_path / "events.json"),
            ))
            job.summary["metrics"] = metrics["summary"]
            job.summary["events"] = len(events)
            job.summary["events_detail"] = events
            job.summary["series"] = series
            exports = _write_exports(job.id, events, metrics)
            manifest.items.extend(exports)
            if on_update:
                await on_update(job)

        if stage == "exports":
            save_json(artifacts_path / "manifest.json", manifest.model_dump())
            manifest.items.append(ArtifactItem(
                name="manifest",
                kind="artifact",
                path=str(artifacts_path / "manifest.json"),
                content_type="application/json",
                size_bytes=file_size(artifacts_path / "manifest.json"),
            ))

    job.status = JobStatus.completed
    job.progress = 1.0
    job.stage = "completed"
    job.updated_at = datetime.utcnow()
    job.summary.pop("series", None)
    job.summary.pop("events_detail", None)
    if on_update:
        await on_update(job)

    return manifest
