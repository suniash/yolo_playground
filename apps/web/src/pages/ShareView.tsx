import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import {
  API_URL,
  getShareEvents,
  getShareJob,
  getShareMetrics,
  getShareTracks,
} from "../api";
import EventTimeline from "../components/EventTimeline";
import MetricsPanel from "../components/MetricsPanel";
import VideoOverlay from "../components/VideoOverlay";

const ShareView = () => {
  const { shareId } = useParams();
  const [job, setJob] = useState<any | null>(null);
  const [tracks, setTracks] = useState<any | null>(null);
  const [metrics, setMetrics] = useState<any | null>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const inputSrc = useMemo(() => {
    if (!shareId) return null;
    return `${API_URL}/api/share/${shareId}/input`;
  }, [shareId]);

  useEffect(() => {
    if (!shareId) return;
    const load = async () => {
      const jobData = await getShareJob(shareId);
      setJob(jobData);
      const [tracksData, metricsData, eventsData] = await Promise.all([
        getShareTracks(shareId),
        getShareMetrics(shareId),
        getShareEvents(shareId),
      ]);
      setTracks(tracksData);
      setMetrics(metricsData);
      setEvents(eventsData.events ?? []);
      setLoading(false);
    };
    load();
  }, [shareId]);

  const handleEventSelect = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      videoRef.current.play();
    }
  };

  if (loading) {
    return <div className="panel">Loading shared view...</div>;
  }

  if (!job) {
    return <div className="panel">Share link invalid.</div>;
  }

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Shared analysis</h1>
          <p>Job {job.id.slice(0, 8)}</p>
        </div>
      </div>

      <div className="studio-layout">
        <div className="video-panel">
          {inputSrc ? (
            <VideoOverlay
              src={inputSrc}
              tracks={tracks}
              showPlayers
              showBall
              showTrails={false}
              onReady={(video) => (videoRef.current = video)}
            />
          ) : (
            <div className="panel">No video input available.</div>
          )}
        </div>
        <div className="right-panel">
          <MetricsPanel metrics={metrics} />
          <EventTimeline events={events} onSelect={handleEventSelect} />
        </div>
      </div>
    </section>
  );
};

export default ShareView;
