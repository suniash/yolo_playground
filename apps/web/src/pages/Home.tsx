import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { API_KEY, API_URL, JobRecord, listJobs } from "../api";

const statusTone: Record<string, string> = {
  queued: "status-chip status-queued",
  processing: "status-chip status-processing",
  completed: "status-chip status-completed",
  failed: "status-chip status-failed",
};

const Home = () => {
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    listJobs()
      .then((data) => {
        if (active) setJobs(data);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    const url = new URL(`${API_URL}/api/updates/jobs`);
    if (API_KEY) {
      url.searchParams.set("api_key", API_KEY);
    }
    const source = new EventSource(url.toString());
    source.addEventListener("list", (event) => {
      const data = JSON.parse((event as MessageEvent).data) as JobRecord[];
      setJobs(data);
    });
    source.addEventListener("job", (event) => {
      const data = JSON.parse((event as MessageEvent).data) as JobRecord;
      setJobs((prev) => {
        const exists = prev.some((job) => job.id === data.id);
        if (exists) {
          return prev.map((job) => (job.id === data.id ? data : job));
        }
        return [data, ...prev];
      });
    });

    return () => {
      active = false;
      source.close();
    };
  }, []);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Projects</h1>
          <p>Track every analysis run, from upload to export.</p>
        </div>
        <Link className="btn-primary" to="/new">
          New Analysis
        </Link>
      </div>

      {loading && <div className="panel">Loading jobs...</div>}

      {!loading && jobs.length === 0 && (
        <div className="panel empty-state">
          <h3>No jobs yet</h3>
          <p>Upload a match clip to start your first analysis.</p>
          <Link className="btn-secondary" to="/new">
            Start a job
          </Link>
        </div>
      )}

      <div className="grid">
        {jobs.map((job) => (
          <Link key={job.id} to={`/jobs/${job.id}`} className="job-card">
            <div className="job-card-header">
              <div>
                <div className="job-title">{job.config?.profile || "soccer"}</div>
                <div className="job-sub">{new Date(job.created_at).toLocaleString()}</div>
              </div>
              <span className={statusTone[job.status]}>{job.status}</span>
            </div>
            <div className="job-card-body">
              <div className="metric">
                <span>Progress</span>
                <strong>{Math.round(job.progress * 100)}%</strong>
              </div>
              <div className="metric">
                <span>Events</span>
                <strong>{job.summary?.events ?? "-"}</strong>
              </div>
              <div className="metric">
                <span>Possession</span>
                <strong>
                  {job.summary?.metrics
                    ? `${Math.round(
                        (job.summary.metrics as any).team_possession.A * 100
                      )}% / ${Math.round(
                        (job.summary.metrics as any).team_possession.B * 100
                      )}%`
                    : "-"}
                </strong>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
};

export default Home;
