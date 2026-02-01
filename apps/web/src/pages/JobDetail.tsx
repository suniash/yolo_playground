import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import {
  API_URL,
  JobRecord,
  getEvents,
  getJob,
  getJobConfig,
  getMetrics,
  getTracks,
  rerunAnalytics,
  updateJobConfig,
} from "../api";
import CalibrationEditor, {
  CalibrationPointDraft,
} from "../components/CalibrationEditor";
import EventTimeline from "../components/EventTimeline";
import MetricsPanel from "../components/MetricsPanel";
import VideoOverlay from "../components/VideoOverlay";
import ZoneEditor, { ZoneDraft } from "../components/ZoneEditor";

const JobDetail = () => {
  const { jobId } = useParams();
  const [job, setJob] = useState<JobRecord | null>(null);
  const [tracks, setTracks] = useState<any | null>(null);
  const [metrics, setMetrics] = useState<any | null>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showPlayers, setShowPlayers] = useState(true);
  const [showBall, setShowBall] = useState(true);
  const [showTrails, setShowTrails] = useState(false);
  const [rerunLoading, setRerunLoading] = useState(false);
  const [zones, setZones] = useState<ZoneDraft[]>([]);
  const [calibrationPoints, setCalibrationPoints] = useState<
    CalibrationPointDraft[]
  >([]);
  const [zonesSaving, setZonesSaving] = useState(false);
  const [zonesError, setZonesError] = useState<string | null>(null);
  const [calibrationSaving, setCalibrationSaving] = useState(false);
  const [calibrationError, setCalibrationError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const inputSrc = useMemo(() => {
    if (!jobId) return null;
    return `${API_URL}/api/jobs/${jobId}/input`;
  }, [jobId]);

  useEffect(() => {
    if (!jobId) return;

    let active = true;
    const loadJob = async () => {
      const data = await getJob(jobId);
      if (!active) return;
      setJob(data);
      setLoading(false);
      return data;
    };

    const poll = async () => {
      const data = await loadJob();
      if (data && data.status !== "completed" && data.status !== "failed") {
        setTimeout(poll, 2000);
      }
    };

    poll();
    return () => {
      active = false;
    };
  }, [jobId]);

  useEffect(() => {
    if (!jobId) return;

    const loadConfig = async () => {
      const config = await getJobConfig(jobId);
      const zoneDrafts = (config.zones as any[] | undefined)?.map((zone) => ({
        id: zone.id,
        name: zone.name,
        points: (zone.polygon || [])
          .map((pair: number[]) => `${pair[0]},${pair[1]}`)
          .join("; "),
      }));
      const calibrationDrafts = (config.calibration_points as any[] | undefined)?.map(
        (point) => ({
          image_x: String(point.image_x ?? ""),
          image_y: String(point.image_y ?? ""),
          field_x: String(point.field_x ?? ""),
          field_y: String(point.field_y ?? ""),
        })
      );
      setZones(zoneDrafts ?? []);
      setCalibrationPoints(calibrationDrafts ?? []);
    };

    loadConfig();
  }, [jobId]);

  useEffect(() => {
    if (!jobId || !job || job.status !== "completed") return;

    const loadArtifacts = async () => {
      const [tracksData, metricsData, eventsData] = await Promise.all([
        getTracks(jobId),
        getMetrics(jobId),
        getEvents(jobId),
      ]);
      setTracks(tracksData);
      setMetrics(metricsData);
      setEvents(eventsData.events ?? []);
    };

    loadArtifacts();
  }, [jobId, job]);

  const parsePolygon = (raw: string) => {
    return raw
      .split(";")
      .map((item) => item.trim())
      .filter(Boolean)
      .map((pair) => pair.split(",").map((value) => Number(value.trim())))
      .filter((pair) => pair.length === 2 && pair.every((value) => !Number.isNaN(value)));
  };

  const handleZoneSave = async () => {
    if (!jobId) return;
    setZonesSaving(true);
    setZonesError(null);
    try {
      const payloadZones = zones.map((zone, index) => {
        const polygon = parsePolygon(zone.points);
        if (polygon.length < 3) {
          throw new Error(`Zone ${zone.name || index + 1} needs at least 3 points.`);
        }
        return {
          id: zone.id || `zone-${index + 1}`,
          name: zone.name || `Zone ${index + 1}`,
          polygon,
        };
      });
      await updateJobConfig(jobId, { zones: payloadZones });
    } catch (err) {
      setZonesError((err as Error).message);
    } finally {
      setZonesSaving(false);
    }
  };

  const handleCalibrationSave = async () => {
    if (!jobId) return;
    setCalibrationSaving(true);
    setCalibrationError(null);
    try {
      const payloadPoints = calibrationPoints.map((point, index) => {
        const imageX = Number(point.image_x);
        const imageY = Number(point.image_y);
        const fieldX = Number(point.field_x);
        const fieldY = Number(point.field_y);
        if ([imageX, imageY, fieldX, fieldY].some((value) => Number.isNaN(value))) {
          throw new Error(`Calibration point ${index + 1} has invalid values.`);
        }
        return {
          image_x: imageX,
          image_y: imageY,
          field_x: fieldX,
          field_y: fieldY,
        };
      });
      await updateJobConfig(jobId, { calibration_points: payloadPoints });
    } catch (err) {
      setCalibrationError((err as Error).message);
    } finally {
      setCalibrationSaving(false);
    }
  };

  const handleEventSelect = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      videoRef.current.play();
    }
  };

  const handleRerun = async () => {
    if (!jobId) return;
    try {
      setRerunLoading(true);
      const updated = await rerunAnalytics(jobId);
      setJob(updated);
    } finally {
      setRerunLoading(false);
    }
  };

  if (loading) {
    return <div className="panel">Loading job...</div>;
  }

  if (!job) {
    return <div className="panel">Job not found.</div>;
  }

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Results Studio</h1>
          <p>Job {job.id.slice(0, 8)} · {job.status}</p>
        </div>
        <div className="header-actions">
          <button className="btn-secondary" onClick={handleRerun} disabled={rerunLoading}>
            {rerunLoading ? "Re-running..." : "Re-run analytics"}
          </button>
          <a className="btn-primary" href={`${API_URL}/api/jobs/${job.id}/artifacts/report_html`}>
            Download report
          </a>
        </div>
      </div>

      <div className="studio-layout">
        <div className="video-panel">
          {inputSrc ? (
            <VideoOverlay
              src={inputSrc}
              tracks={tracks}
              showPlayers={showPlayers}
              showBall={showBall}
              showTrails={showTrails}
              onReady={(video) => (videoRef.current = video)}
            />
          ) : (
            <div className="panel">No video input available.</div>
          )}
          <div className="overlay-controls">
            <label>
              <input
                type="checkbox"
                checked={showPlayers}
                onChange={(event) => setShowPlayers(event.target.checked)}
              />
              Players
            </label>
            <label>
              <input
                type="checkbox"
                checked={showBall}
                onChange={(event) => setShowBall(event.target.checked)}
              />
              Ball
            </label>
            <label>
              <input
                type="checkbox"
                checked={showTrails}
                onChange={(event) => setShowTrails(event.target.checked)}
              />
              Ball trail
            </label>
          </div>
        </div>

        <div className="right-panel">
          <MetricsPanel metrics={metrics} />
          <EventTimeline events={events} onSelect={handleEventSelect} />
          <ZoneEditor
            zones={zones}
            onUpdate={(index, zone) => {
              setZones((prev) => prev.map((item, idx) => (idx === index ? zone : item)));
            }}
            onAdd={() =>
              setZones((prev) => [
                ...prev,
                { id: `zone-${Date.now()}`, name: "", points: "" },
              ])
            }
            onRemove={(index) =>
              setZones((prev) => prev.filter((_, idx) => idx !== index))
            }
            onSave={handleZoneSave}
            saving={zonesSaving}
            error={zonesError}
          />
          <CalibrationEditor
            points={calibrationPoints}
            onUpdate={(index, point) =>
              setCalibrationPoints((prev) =>
                prev.map((item, idx) => (idx === index ? point : item))
              )
            }
            onAdd={() =>
              setCalibrationPoints((prev) => [
                ...prev,
                { image_x: "", image_y: "", field_x: "", field_y: "" },
              ])
            }
            onRemove={(index) =>
              setCalibrationPoints((prev) => prev.filter((_, idx) => idx !== index))
            }
            onSave={handleCalibrationSave}
            saving={calibrationSaving}
            error={calibrationError}
          />
          <div className="panel">
            <div className="panel-header">
              <h3>Exports</h3>
            </div>
            <div className="export-grid">
              <a href={`${API_URL}/api/jobs/${job.id}/artifacts/events_csv`}>Events CSV</a>
              <a href={`${API_URL}/api/jobs/${job.id}/artifacts/summary_csv`}>Summary CSV</a>
              <a href={`${API_URL}/api/jobs/${job.id}/artifacts/tracks`}>Tracks JSON</a>
              <a href={`${API_URL}/api/jobs/${job.id}/artifacts/metrics`}>Metrics JSON</a>
              <a href={`${API_URL}/api/jobs/${job.id}/artifacts/events`}>Events JSON</a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default JobDetail;
