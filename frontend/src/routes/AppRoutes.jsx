// All page routes, grouped into public, author-only and admin-only.
import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute, { GuestOnly } from "./ProtectedRoute";
import AuthorLayout from "../components/layout/AuthorLayout";
import AdminLayout from "../components/layout/AdminLayout";
import LoginPage from "../pages/auth/LoginPage";
import SignupPage from "../pages/auth/SignupPage";
import MyBooksPage from "../pages/author/MyBooksPage";
import MyTicketsPage from "../pages/author/MyTicketsPage";
import NewTicketPage from "../pages/author/NewTicketPage";
import TicketDetailPage from "../pages/author/TicketDetailPage";
import TicketQueuePage from "../pages/admin/TicketQueuePage";
import AdminTicketPage from "../pages/admin/AdminTicketPage";
import NotFoundPage from "../pages/NotFoundPage";
import { homeFor, useAuth } from "../context/AuthContext";
import { PageLoader } from "../components/common/Spinner";

function Home() {
  const { user, checking } = useAuth();
  if (checking) return <PageLoader />;
  return <Navigate to={user ? homeFor(user) : "/login"} replace />;
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />

      <Route element={<GuestOnly />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
      </Route>

      <Route element={<ProtectedRoute role="AUTHOR" />}>
        <Route element={<AuthorLayout />}>
          <Route path="/books" element={<MyBooksPage />} />
          <Route path="/tickets" element={<MyTicketsPage />} />
          <Route path="/tickets/new" element={<NewTicketPage />} />
          <Route path="/tickets/:number" element={<TicketDetailPage />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute role="ADMIN" />}>
        <Route element={<AdminLayout />}>
          <Route path="/admin" element={<TicketQueuePage />} />
          <Route path="/admin/tickets/:number" element={<AdminTicketPage />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
