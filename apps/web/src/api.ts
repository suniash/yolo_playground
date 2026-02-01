export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export type JobStatus = "queued" | "processing" | "completed" | "failed";

export interface JobRecord {
  id: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  progress: number;
  stage?: string | null;
  config: { profile: string };
  summary?: Record<string, unknown>;
  input?: { filename: string; path: string };
}

export const fetchJson = async <T>(path: string): Promise<T> => {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
};

export const listJobs = () => fetchJson<JobRecord[]>("/api/jobs");
export const getJob = (id: string) => fetchJson<JobRecord>(`/api/jobs/${id}`);
export const getTracks = (id: string) => fetchJson<any>(`/api/jobs/${id}/tracks`);
export const getEvents = (id: string) => fetchJson<any>(`/api/jobs/${id}/events`);
export const getMetrics = (id: string) => fetchJson<any>(`/api/jobs/${id}/metrics`);

export const createJob = async (payload: {
  file: File;
  profile: string;
  analyticsEnabled: boolean;
}) => {
  const form = new FormData();
  form.append("video", payload.file);
  form.append(
    "config",
    JSON.stringify({
      profile: payload.profile,
      analytics_enabled: payload.analyticsEnabled,
    })
  );
  const response = await fetch(`${API_URL}/api/jobs`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
};

export const rerunAnalytics = async (jobId: string) => {
  const response = await fetch(`${API_URL}/api/jobs/${jobId}/rerun`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
};
