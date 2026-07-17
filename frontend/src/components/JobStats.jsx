export default function JobStats({ stats }) {
  if (!stats) return null;
  const s = stats.score_summary;

  return (
    <div className="stats-bar">
      <div className="stat">
        <div className="stat-value">{stats.total}</div>
        <div className="stat-label">Applicants</div>
      </div>
      <div className="stat">
        <div className="stat-value">{stats.by_status.shortlisted || 0}</div>
        <div className="stat-label">Shortlisted</div>
      </div>
      <div className="stat">
        <div className="stat-value">{stats.processing}</div>
        <div className="stat-label">Processing</div>
      </div>
      <div className="stat">
        <div className="stat-value">{s ? s.average : "—"}</div>
        <div className="stat-label">Avg score</div>
      </div>
      <div className="stat">
        <div className="stat-value">{s ? s.max : "—"}</div>
        <div className="stat-label">Top score</div>
      </div>
      {stats.top_skills.length > 0 && (
        <div className="stat stat-skills">
          <div className="stat-label">Top skills</div>
          <div className="skill-chips">
            {stats.top_skills.slice(0, 6).map((sk) => (
              <span key={sk.skill} className="chip">
                {sk.skill} <span className="chip-count">{sk.count}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
