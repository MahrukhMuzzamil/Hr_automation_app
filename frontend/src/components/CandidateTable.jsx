import { candidatesApi } from "../api/recruitment";

const STATUS_LABELS = {
  pending: "Pending",
  processing: "Processing",
  shortlisted: "Shortlisted",
  rejected: "Rejected",
  failed: "Failed",
};

function StatusBadge({ status, manual }) {
  return (
    <span className={`badge badge-${status}`}>
      {STATUS_LABELS[status] || status}
      {manual && <span className="badge-manual" title="Manual recruiter decision"> ·M</span>}
    </span>
  );
}

export default function CandidateTable({
  candidates,
  onReprocess,
  onDecide,
  onOpenNotes,
}) {
  if (candidates.length === 0) {
    return <p className="muted">No candidates match the current filters.</p>;
  }

  const decided = (c) => ["pending", "processing"].includes(c.status);

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
            <th>Decision</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((c) => (
            <tr key={c.id}>
              <td>
                <button
                  className="link-button cand-name"
                  onClick={() => onOpenNotes?.(c)}
                  title="View notes"
                >
                  {c.name || "—"}
                </button>
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
                <StatusBadge status={c.status} manual={c.is_manual_decision} />
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
                <div className="decision-actions">
                  {c.status !== "shortlisted" && (
                    <button
                      className="btn btn-ghost small"
                      onClick={() => onDecide?.(c.id, "shortlist")}
                      disabled={decided(c)}
                    >
                      Shortlist
                    </button>
                  )}
                  {c.status !== "rejected" && (
                    <button
                      className="btn btn-ghost small"
                      onClick={() => onDecide?.(c.id, "reject")}
                      disabled={decided(c)}
                    >
                      Reject
                    </button>
                  )}
                  {c.is_manual_decision && (
                    <button
                      className="btn btn-ghost small"
                      onClick={() => onDecide?.(c.id, "reset")}
                      title="Revert to AI scoring"
                    >
                      Reset
                    </button>
                  )}
                </div>
              </td>
              <td>
                {["failed", "rejected"].includes(c.status) &&
                  !c.is_manual_decision && (
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
