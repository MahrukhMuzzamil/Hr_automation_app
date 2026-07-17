import client from "./client";

export const authApi = {
  login: (username, password) =>
    client.post("/auth/login/", { username, password }).then((r) => r.data),
  me: () => client.get("/auth/me/").then((r) => r.data),
};

export const jobsApi = {
  list: () => client.get("/jobs/").then((r) => r.data),
  get: (id) => client.get(`/jobs/${id}/`).then((r) => r.data),
  create: (payload) => client.post("/jobs/", payload).then((r) => r.data),
  candidates: (id, params = {}) =>
    client.get(`/jobs/${id}/candidates/`, { params }).then((r) => r.data),
};

export const candidatesApi = {
  get: (id) => client.get(`/candidates/${id}/`).then((r) => r.data),
  upload: (jobId, file, onProgress) => {
    const form = new FormData();
    form.append("job", jobId);
    form.append("resume", file);
    return client
      .post("/candidates/upload/", form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: onProgress,
      })
      .then((r) => r.data);
  },
  reprocess: (id) =>
    client.post(`/candidates/${id}/reprocess/`).then((r) => r.data),
  resumeUrl: (id) => `${client.defaults.baseURL}/candidates/${id}/resume/`,
};
