from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class SportProfile(str, Enum):
    soccer = "soccer"
    basketball = "basketball"


class CalibrationPoint(BaseModel):
    image_x: float
    image_y: float
    field_x: float
    field_y: float


class ZoneDefinition(BaseModel):
    id: str
    name: str
    polygon: list[list[float]]


class JobConfig(BaseModel):
    profile: SportProfile = SportProfile.soccer
    analytics_enabled: bool = True
    calibration_points: list[CalibrationPoint] = Field(default_factory=list)
    zones: list[ZoneDefinition] = Field(default_factory=list)
    thresholds: dict[str, float] = Field(default_factory=dict)


class JobConfigUpdate(BaseModel):
    profile: Optional[SportProfile] = None
    analytics_enabled: Optional[bool] = None
    calibration_points: Optional[list[CalibrationPoint]] = None
    zones: Optional[list[ZoneDefinition]] = None
    thresholds: Optional[dict[str, float]] = None


class InputAsset(BaseModel):
    filename: str
    content_type: Optional[str]
    path: str


class ArtifactItem(BaseModel):
    name: str
    kind: Literal["artifact", "export", "input"]
    path: str
    content_type: str
    size_bytes: Optional[int] = None


class ArtifactManifest(BaseModel):
    items: list[ArtifactItem] = Field(default_factory=list)


class JobRecord(BaseModel):
    id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    progress: float = 0.0
    stage: Optional[str] = None
    config: JobConfig
    input: Optional[InputAsset] = None
    error: Optional[str] = None
    manifest: ArtifactManifest = Field(default_factory=ArtifactManifest)
    summary: dict[str, Any] = Field(default_factory=dict)
