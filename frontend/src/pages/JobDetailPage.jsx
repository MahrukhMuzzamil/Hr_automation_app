import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { candidatesApi, jobsApi } from "../api/recruitment";
import CandidateTable from "../components/CandidateTable";
import JobStats from "../components/JobStats";
import NotesModal from "../components/NotesModal";
import UploadResume from "../components/UploadResume";

export default function JobDetailPage() {
  const { jobId } = useParams();
  const [job, setJob] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [minScore, setMinScore] = useState("");
  const [ordering, setOrdering] = useState("-score");
  const [notesFor, setNotesFor] = useState(null);
  const [exporting, setExporting] = useState(false);

  const loadCandidates = useCallback(() => {
    const params = { ordering };
    if (statusFilter) params.status = statusFilter;
    if (minScore) params.min_score = minScore;
    return jobsApi
      .candidates(jobId, params)
      .then((data) => setCandidates(data.results || data));
  }, [jobId, ordering, statusFilter, minScore]);

  const loadStats = useCallback(
    () => jobsApi.stats(jobId).then(setStats),
    [jobId]
  );

  useEffect(() => {
    setLoading(true);
    Promise.all([
      jobsApi.get(jobId).then(setJob),
      loadCandidates(),
      loadStats(),
    ]).finally(() => setLoading(false));
  }, [jobId, loadCandidates, loadStats]);

  // Poll while any candidate is still processing so scores appear live.
  useEffect(() => {
    const pending = candidates.some((c) =>
      ["pending", "processing"].includes(c.status)
    );
    if (!pending) return undefined;
    const timer = setInterval(() => {
      loadCandidates();
      loadStats();
    }, 4000);
    return () => clearInterval(timer);
  }, [candidates, loadCandidates, loadStats]);

  const refresh = useCallback(
    () => Promise.all([loadCandidates(), loadStats()]),
    [loadCandidates, loadStats]
  );

  const reprocess = async (id) => {
    await candidatesApi.reprocess(id);
    refresh();
  };

  const decide = async (id, decision) => {
    let note;
    if (decision !== "reset") {
      note = window.prompt(`Optional note for this ${decision}:`) || "";
    }
    await candidatesApi.decide(id, decision, note);
    refresh();
  };

  const exportCsv = async () => {
    setExporting(true);
    try {
      const blob = await jobsApi.exportCsv(jobId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `candidates_${jobId}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
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
              {job.location ? ` · ${job.location}` : ""}
            </p>
          </div>
          <button
            className="btn btn-ghost"
            onClick={exportCsv}
            disabled={exporting || (stats && stats.total === 0)}
          >
            {exporting ? "Exporting…" : "Export CSV"}
          </button>
        </div>
      )}

      <JobStats stats={stats} />

      <UploadResume jobId={jobId} onUploaded={refresh} />

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

        <CandidateTable
          candidates={candidates}
          onReprocess={reprocess}
          onDecide={decide}
          onOpenNotes={setNotesFor}
        />
      </div>

      {notesFor && (
        <NotesModal candidate={notesFor} onClose={() => setNotesFor(null)} />
      )}
    </div>
  );
}
