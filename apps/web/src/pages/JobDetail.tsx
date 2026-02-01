import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import {
  API_URL,
  JobRecord,
  getEvents,
  getJob,
  getMetrics,
  getTracks,
  rerunAnalytics,
} from "../api";
import EventTimeline from "../components/EventTimeline";
import MetricsPanel from "../components/MetricsPanel";
import VideoOverlay from "../components/VideoOverlay";

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
