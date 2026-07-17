import { candidatesApi } from "../api/recruitment";

const STATUS_LABELS = {
  pending: "Pending",
  processing: "Processing",
  shortlisted: "Shortlisted",
  rejected: "Rejected",
  failed: "Failed",
};

function StatusBadge({ status }) {
  return (
    <span className={`badge badge-${status}`}>
      {STATUS_LABELS[status] || status}
    </span>
  );
}

export default function CandidateTable({ candidates, onReprocess }) {
  if (candidates.length === 0) {
    return <p className="muted">No candidates match the current filters.</p>;
  }

  return (
    <div className="table-wrap">
      <table className="candidate-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Score</th>
            <th>Status</th>
            <th>Experience</th>
            <th>Resume</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((c) => (
            <tr key={c.id}>
              <td>
                <div className="cand-name">{c.name || "—"}</div>
                {c.email && <div className="muted small">{c.email}</div>}
              </td>
              <td>
                {c.score != null ? (
                  <span className="score">{Math.round(c.score)}</span>
                ) : (
                  <span className="muted">—</span>
                )}
              </td>
              <td>
                <StatusBadge status={c.status} />
              </td>
              <td>
                {c.total_experience_years != null
                  ? `${c.total_experience_years} yr`
                  : "—"}
              </td>
              <td>
                <a
                  href={candidatesApi.resumeUrl(c.id)}
                  target="_blank"
                  rel="noreferrer"
                >
                  Download
                </a>
              </td>
              <td>
                {["failed", "rejected"].includes(c.status) && (
                  <button
                    className="btn btn-ghost small"
                    onClick={() => onReprocess(c.id)}
                  >
                    Re-run
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
