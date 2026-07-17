import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (isAuthenticated) navigate("/jobs", { replace: true });

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(username, password);
      navigate("/jobs", { replace: true });
    } catch (err) {
      setError(
        err.response?.status === 401
          ? "Invalid username or password."
          : "Login failed. Please try again."
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="center">
      <form className="card login-card" onSubmit={onSubmit}>
        <h1>🧭 HR Screening</h1>
        <p className="muted">Recruiter sign in</p>
        {error && <div className="alert alert-error">{error}</div>}
        <label>
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        <button className="btn btn-primary" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
