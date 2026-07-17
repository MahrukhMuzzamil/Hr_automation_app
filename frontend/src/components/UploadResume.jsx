import { useRef, useState } from "react";
import { candidatesApi } from "../api/recruitment";

export default function UploadResume({ jobId, onUploaded }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState(null);

  const handleFiles = async (files) => {
    if (!files || files.length === 0) return;
    setBusy(true);
    setMessage(null);
    let ok = 0;
    let failed = 0;

    for (const file of files) {
      try {
        await candidatesApi.upload(jobId, file, (e) => {
          if (e.total) setProgress(Math.round((e.loaded / e.total) * 100));
        });
        ok += 1;
      } catch (err) {
        failed += 1;
      }
    }

    setBusy(false);
    setProgress(0);
    if (inputRef.current) inputRef.current.value = "";
    setMessage({
      type: failed ? "error" : "success",
      text: `Uploaded ${ok} resume(s)${failed ? `, ${failed} failed` : ""}. Processing in the background…`,
    });
    onUploaded?.();
  };

  return (
    <div className="card upload-card">
      <div className="upload-row">
        <div>
          <strong>Upload resumes</strong>
          <p className="muted small">
            PDF or DOCX. Each is parsed and scored against this job's
            requirements automatically.
          </p>
        </div>
        <div>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx,.doc"
            multiple
            disabled={busy}
            onChange={(e) => handleFiles(Array.from(e.target.files))}
          />
        </div>
      </div>
      {busy && (
        <div className="progress">
          <div className="progress-bar" style={{ width: `${progress}%` }} />
        </div>
      )}
      {message && (
        <div className={`alert alert-${message.type}`}>{message.text}</div>
      )}
    </div>
  );
}
