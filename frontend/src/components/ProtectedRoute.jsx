import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) return <div className="center muted">Loading…</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
}
