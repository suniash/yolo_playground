export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
export const API_KEY = import.meta.env.VITE_API_KEY || "";

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

const withAuth = (headers?: HeadersInit): HeadersInit =>
  API_KEY ? { ...headers, "X-API-Key": API_KEY } : headers ?? {};

export const fetchJson = async <T>(
  path: string,
  options?: RequestInit
): Promise<T> => {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: withAuth(options?.headers),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
};

export const listJobs = () => fetchJson<JobRecord[]>("/api/jobs");
export const getJob = (id: string) =>
  fetchJson<JobRecord>(`/api/jobs/${id}`);
export const getJobConfig = (id: string) =>
  fetchJson<Record<string, unknown>>(`/api/jobs/${id}/config`);
export const getTracks = (id: string) =>
  fetchJson<any>(`/api/jobs/${id}/tracks`);
export const getEvents = (id: string) =>
  fetchJson<any>(`/api/jobs/${id}/events`);
export const getMetrics = (id: string) =>
  fetchJson<any>(`/api/jobs/${id}/metrics`);

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
    headers: withAuth(),
    body: form,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
};

export const rerunAnalytics = async (
  jobId: string,
  updates?: Record<string, unknown>
) => {
  const response = await fetch(`${API_URL}/api/jobs/${jobId}/rerun`, {
    method: "POST",
    headers: withAuth(
      updates ? { "Content-Type": "application/json" } : undefined
    ),
    body: updates ? JSON.stringify(updates) : undefined,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
};

export const updateJobConfig = async (
  jobId: string,
  updates: Record<string, unknown>
) => {
  const response = await fetch(`${API_URL}/api/jobs/${jobId}/config`, {
    method: "PATCH",
    headers: withAuth({ "Content-Type": "application/json" }),
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
};

export const createShareLink = async (jobId: string, ttlHours?: number) => {
  const url = new URL(`${API_URL}/api/jobs/${jobId}/share`);
  if (ttlHours) {
    url.searchParams.set("ttl_hours", String(ttlHours));
  }
  const response = await fetch(url.toString(), {
    method: "POST",
    headers: withAuth(),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
};

export const getShareJob = (shareId: string) =>
  fetchJson<JobRecord>(`/api/share/${shareId}/job`);
export const getShareTracks = (shareId: string) =>
  fetchJson<any>(`/api/share/${shareId}/tracks`);
export const getShareMetrics = (shareId: string) =>
  fetchJson<any>(`/api/share/${shareId}/metrics`);
export const getShareEvents = (shareId: string) =>
  fetchJson<any>(`/api/share/${shareId}/events`);
