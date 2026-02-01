import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createJob } from "../api";

const NewAnalysis = () => {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [profile, setProfile] = useState("soccer");
  const [analyticsEnabled, setAnalyticsEnabled] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) {
      setError("Please select a video file.");
      return;
    }

    try {
      setSubmitting(true);
      const job = await createJob({ file, profile, analyticsEnabled });
      navigate(`/jobs/${job.id}`);
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
        <label className="field">
          <span>Video file</span>
          <input
            type="file"
            accept="video/*"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>

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
