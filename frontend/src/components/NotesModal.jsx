import { useEffect, useState } from "react";
import { candidatesApi } from "../api/recruitment";

export default function NotesModal({ candidate, onClose }) {
  const [notes, setNotes] = useState([]);
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    candidatesApi
      .notes(candidate.id)
      .then((data) => active && setNotes(data))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [candidate.id]);

  const submit = async (e) => {
    e.preventDefault();
    const text = body.trim();
    if (!text) return;
    setSaving(true);
    try {
      const note = await candidatesApi.addNote(candidate.id, text);
      setNotes((prev) => [note, ...prev]);
      setBody("");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>Notes · {candidate.name || "Candidate"}</h3>
          <button className="btn btn-ghost small" onClick={onClose}>
            Close
          </button>
        </div>

        <form className="note-form" onSubmit={submit}>
          <textarea
            rows={3}
            value={body}
            placeholder="Add a note (interview feedback, availability, …)"
            onChange={(e) => setBody(e.target.value)}
          />
          <button className="btn" type="submit" disabled={saving || !body.trim()}>
            {saving ? "Saving…" : "Add note"}
          </button>
        </form>

        <div className="note-list">
          {loading ? (
            <p className="muted">Loading…</p>
          ) : notes.length === 0 ? (
            <p className="muted">No notes yet.</p>
          ) : (
            notes.map((n) => (
              <div key={n.id} className="note-item">
                <div className="note-body">{n.body}</div>
                <div className="muted small">
                  {n.author_name || "Unknown"} ·{" "}
                  {new Date(n.created_at).toLocaleString()}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
