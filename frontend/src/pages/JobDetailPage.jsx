import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { candidatesApi, jobsApi } from "../api/recruitment";
import CandidateTable from "../components/CandidateTable";
import UploadResume from "../components/UploadResume";

export default function JobDetailPage() {
  const { jobId } = useParams();
  const [job, setJob] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [minScore, setMinScore] = useState("");
  const [ordering, setOrdering] = useState("-score");

  const loadCandidates = useCallback(() => {
    const params = { ordering };
    if (statusFilter) params.status = statusFilter;
    if (minScore) params.min_score = minScore;
    return jobsApi
      .candidates(jobId, params)
      .then((data) => setCandidates(data.results || data));
  }, [jobId, ordering, statusFilter, minScore]);

  useEffect(() => {
    setLoading(true);
    Promise.all([jobsApi.get(jobId).then(setJob), loadCandidates()]).finally(() =>
      setLoading(false)
    );
  }, [jobId, loadCandidates]);

  // Poll while any candidate is still processing so scores appear live.
  useEffect(() => {
    const pending = candidates.some((c) =>
      ["pending", "processing"].includes(c.status)
    );
    if (!pending) return undefined;
    const timer = setInterval(loadCandidates, 4000);
    return () => clearInterval(timer);
  }, [candidates, loadCandidates]);

  const reprocess = async (id) => {
    await candidatesApi.reprocess(id);
    loadCandidates();
  };

  if (loading && !job) return <p className="muted">Loading…</p>;

  return (
    <div>
      <Link to="/jobs" className="back-link">
        ← All jobs
      </Link>

      {job && (
        <div className="page-head">
          <div>
            <h2>{job.title}</h2>
            <p className="muted">
              {job.department || "—"}
              {job.location ? ` · ${job.location}` : ""} ·{" "}
              {job.applicant_count} applicants · {job.shortlisted_count} shortlisted
            </p>
          </div>
        </div>
      )}

      <UploadResume jobId={jobId} onUploaded={loadCandidates} />

      <div className="card">
        <div className="table-controls">
          <label>
            Status
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All</option>
              <option value="shortlisted">Shortlisted</option>
              <option value="rejected">Rejected</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="failed">Failed</option>
            </select>
          </label>
          <label>
            Min score
            <input
              type="number"
              min="0"
              max="100"
              value={minScore}
              onChange={(e) => setMinScore(e.target.value)}
              placeholder="0"
            />
          </label>
          <label>
            Sort
            <select value={ordering} onChange={(e) => setOrdering(e.target.value)}>
              <option value="-score">Score (high → low)</option>
              <option value="score">Score (low → high)</option>
              <option value="-created_at">Newest first</option>
              <option value="name">Name (A → Z)</option>
            </select>
          </label>
        </div>

        <CandidateTable candidates={candidates} onReprocess={reprocess} />
      </div>
    </div>
  );
}
