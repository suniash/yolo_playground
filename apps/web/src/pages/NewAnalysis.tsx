import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createJob, createStreamJob } from "../api";

const NewAnalysis = () => {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [streamUrl, setStreamUrl] = useState("");
  const [inputMode, setInputMode] = useState<"upload" | "stream">("upload");
  const [profile, setProfile] = useState("soccer");
  const [analyticsEnabled, setAnalyticsEnabled] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    try {
      setSubmitting(true);
      if (inputMode === "upload") {
        if (!file) {
          setError("Please select a video file.");
          return;
        }
        const job = await createJob({ file, profile, analyticsEnabled });
        navigate(`/jobs/${job.id}`);
      } else {
        if (!streamUrl) {
          setError("Please enter a stream URL.");
          return;
        }
        const job = await createStreamJob({ streamUrl, profile, analyticsEnabled });
        navigate(`/jobs/${job.id}`);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>New Analysis</h1>
          <p>Upload a clip, pick a sport profile, run the pipeline.</p>
        </div>
      </div>

      <form className="panel form" onSubmit={handleSubmit}>
        <div className="toggle-row">
          <label>
            <input
              type="radio"
              name="input-mode"
              value="upload"
              checked={inputMode === "upload"}
              onChange={() => setInputMode("upload")}
            />
            Upload video
          </label>
          <label>
            <input
              type="radio"
              name="input-mode"
              value="stream"
              checked={inputMode === "stream"}
              onChange={() => setInputMode("stream")}
            />
            Stream URL
          </label>
        </div>

        {inputMode === "upload" ? (
        <label className="field">
          <span>Video file</span>
          <input
            type="file"
            accept="video/*"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>
        ) : (
          <label className="field">
            <span>Stream URL</span>
            <input
              type="url"
              placeholder="https://example.com/stream.m3u8"
              value={streamUrl}
              onChange={(event) => setStreamUrl(event.target.value)}
            />
          </label>
        )}

        <label className="field">
          <span>Sport profile</span>
          <select value={profile} onChange={(event) => setProfile(event.target.value)}>
            <option value="soccer">Soccer</option>
            <option value="basketball">Basketball</option>
          </select>
        </label>

        <label className="field checkbox">
          <input
            type="checkbox"
            checked={analyticsEnabled}
            onChange={(event) => setAnalyticsEnabled(event.target.checked)}
          />
          <span>Enable analytics and events</span>
        </label>

        {error && <div className="alert">{error}</div>}

        <button className="btn-primary" type="submit" disabled={submitting}>
          {submitting ? "Starting analysis..." : "Run analysis"}
        </button>
      </form>
    </section>
  );
};

export default NewAnalysis;
