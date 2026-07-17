import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { jobsApi } from "../api/recruitment";

export default function JobsPage() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);

  const load = () => {
    setLoading(true);
    jobsApi
      .list()
      .then((data) => setJobs(data.results || data))
      .catch(() => setError("Could not load job postings."))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <div>
      <div className="page-head">
        <h2>Job Postings</h2>
        <button className="btn btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Close" : "+ New job"}
        </button>
      </div>

      {showForm && (
        <NewJobForm
          onCreated={() => {
            setShowForm(false);
            load();
          }}
        />
      )}

      {error && <div className="alert alert-error">{error}</div>}
      {loading ? (
        <p className="muted">Loading…</p>
      ) : jobs.length === 0 ? (
        <p className="muted">No job postings yet. Create one to get started.</p>
      ) : (
        <div className="job-grid">
          {jobs.map((job) => (
            <Link key={job.id} to={`/jobs/${job.id}`} className="card job-card">
              <div className="job-card-head">
                <h3>{job.title}</h3>
                {job.is_open ? (
                  <span className="pill pill-open">Open</span>
                ) : (
                  <span className="pill pill-closed">Closed</span>
                )}
              </div>
              <p className="muted">
                {job.department || "—"}
                {job.location ? ` · ${job.location}` : ""}
              </p>
              <div className="job-stats">
                <div>
                  <span className="stat-num">{job.applicant_count}</span>
                  <span className="stat-label">Applicants</span>
                </div>
                <div>
                  <span className="stat-num accent">{job.shortlisted_count}</span>
                  <span className="stat-label">Shortlisted</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function NewJobForm({ onCreated }) {
  const [form, setForm] = useState({
    title: "",
    department: "",
    location: "",
    requirements: "",
    description: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const update = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await jobsApi.create(form);
      onCreated();
    } catch {
      setError("Could not create the job posting.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="card" onSubmit={submit}>
      {error && <div className="alert alert-error">{error}</div>}
      <label>
        Title
        <input value={form.title} onChange={update("title")} required />
      </label>
      <div className="form-row">
        <label>
          Department
          <input value={form.department} onChange={update("department")} />
        </label>
        <label>
          Location
          <input value={form.location} onChange={update("location")} />
        </label>
      </div>
      <label>
        Requirements (used for scoring)
        <textarea
          value={form.requirements}
          onChange={update("requirements")}
          rows={3}
          placeholder="e.g. Python, Django, PostgreSQL, 3+ years backend experience"
          required
        />
      </label>
      <label>
        Description
        <textarea
          value={form.description}
          onChange={update("description")}
          rows={2}
        />
      </label>
      <button className="btn btn-primary" disabled={busy}>
        {busy ? "Creating…" : "Create job"}
      </button>
    </form>
  );
}
