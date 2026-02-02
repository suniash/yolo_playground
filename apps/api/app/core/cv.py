from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .schemas import JobConfig


def _assign_team(track_id: int) -> str:
    return "A" if track_id % 2 == 0 else "B"


def run_ultralytics(input_path: Path, config: JobConfig) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        import cv2  # type: ignore
        from ultralytics import YOLO  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("Ultralytics and OpenCV are required for real CV processing") from exc

    model_name = os.getenv("VAP_MODEL", "yolov8n.pt")
    confidence = float(config.thresholds.get("det_confidence", 0.3))

    cap = cv2.VideoCapture(str(input_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()

    model = YOLO(model_name)
    results = model.track(source=str(input_path), stream=True, persist=True, conf=confidence, verbose=False)

    frames = []
    tracks_map: dict[str, dict[str, Any]] = {}
    player_positions: dict[str, list[tuple[float, float]]] = {}
    ball_positions: list[tuple[float, float]] = []

    last_player_positions: dict[str, tuple[float, float]] = {}
    last_ball: tuple[float, float] | None = None

    frame_idx = 0
    class_names = model.names

    for result in results:
        objects = []
        if result.boxes is None:
            frames.append({"frame": frame_idx, "objects": objects})
            frame_idx += 1
            continue

        xyxy = result.boxes.xyxy.cpu().tolist()
        confs = result.boxes.conf.cpu().tolist()
        classes = result.boxes.cls.cpu().tolist()
        track_ids = result.boxes.id.cpu().tolist() if result.boxes.id is not None else [None] * len(xyxy)

        ball_candidates = []
        frame_players: dict[str, tuple[float, float]] = {}

        for bbox, conf, cls_id, track_id in zip(xyxy, confs, classes, track_ids):
            label = class_names.get(int(cls_id), "")
            if label == "person":
                track_num = int(track_id) if track_id is not None else int(conf * 10000) + frame_idx
                track_key = f"p{track_num}"
                team = _assign_team(track_num)
                tracks_map.setdefault(track_key, {"id": track_key, "label": "player", "team": team})
                x1, y1, x2, y2 = bbox
                w = x2 - x1
                h = y2 - y1
                cx = x1 + w / 2
                cy = y1 + h / 2
                frame_players[track_key] = (cx, cy)
                objects.append({
                    "id": track_key,
                    "label": "player",
                    "team": team,
                    "bbox": [round(x1, 2), round(y1, 2), round(w, 2), round(h, 2)],
                    "confidence": round(conf, 3),
                })
            elif label == "sports ball":
                x1, y1, x2, y2 = bbox
                w = x2 - x1
                h = y2 - y1
                cx = x1 + w / 2
                cy = y1 + h / 2
                ball_candidates.append({
                    "confidence": conf,
                    "center": (cx, cy),
                    "bbox": [round(x1, 2), round(y1, 2), round(w, 2), round(h, 2)],
                })

        if ball_candidates:
            best = max(ball_candidates, key=lambda item: item["confidence"])
            last_ball = best["center"]
            objects.append({
                "id": "ball",
                "label": "ball",
                "team": None,
                "bbox": best["bbox"],
                "confidence": round(best["confidence"], 3),
            })
        elif last_ball is not None:
            cx, cy = last_ball
            objects.append({
                "id": "ball",
                "label": "ball",
                "team": None,
                "bbox": [round(cx - 8, 2), round(cy - 8, 2), 16, 16],
                "confidence": 0.2,
            })

        frames.append({"frame": frame_idx, "objects": objects})

        for track_key in tracks_map.keys():
            if track_key not in player_positions:
                player_positions[track_key] = []
            if track_key in frame_players:
                last_player_positions[track_key] = frame_players[track_key]
            if track_key in last_player_positions:
                player_positions[track_key].append(last_player_positions[track_key])
            else:
                player_positions[track_key].append((0.0, 0.0))

        if last_ball is not None:
            ball_positions.append(last_ball)
        else:
            ball_positions.append((width / 2, height / 2))

        frame_idx += 1

    if frame_count == 0:
        frame_count = frame_idx

    owner_by_frame = []
    last_owner = None
    for idx in range(frame_count):
        ball = ball_positions[idx]
        nearest_id = None
        nearest_dist = None
        for player_id, positions in player_positions.items():
            if idx >= len(positions):
                continue
            px, py = positions[idx]
            dist = (px - ball[0]) ** 2 + (py - ball[1]) ** 2
            if nearest_dist is None or dist < nearest_dist:
                nearest_dist = dist
                nearest_id = player_id
        if nearest_id is None:
            nearest_id = last_owner or (list(player_positions.keys())[0] if player_positions else "p1")
        owner_by_frame.append(nearest_id)
        last_owner = nearest_id

    tracks_data = {
        "meta": {
            "profile": config.profile.value,
            "fps": fps,
            "frame_count": frame_count,
            "width": width,
            "height": height,
        },
        "tracks": list(tracks_map.values()),
        "frames": frames,
    }

    series = {
        "player_positions": player_positions,
        "ball_positions": ball_positions,
        "owner_by_frame": owner_by_frame,
        "fps": fps,
        "width": width,
        "height": height,
    }

    return tracks_data, series
