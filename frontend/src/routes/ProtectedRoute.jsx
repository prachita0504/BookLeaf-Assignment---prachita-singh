// Redirects to /login when logged out, and sends users away from pages their role may not see.
// (The backend enforces the same rules; this only keeps the UI from showing pages that would 403.)
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { homeFor, useAuth } from "../context/AuthContext";
import { PageLoader } from "../components/common/Spinner";

export default function ProtectedRoute({ role }) {
  const { user, checking } = useAuth();
  const location = useLocation();

  if (checking) return <PageLoader />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (role && user.role !== role) return <Navigate to={homeFor(user)} replace />;
  return <Outlet />;
}

/** For /login and /signup: logged-in users go straight to their home page. */
export function GuestOnly() {
  const { user, checking } = useAuth();
  if (checking) return <PageLoader />;
  return user ? <Navigate to={homeFor(user)} replace /> : <Outlet />;
}
