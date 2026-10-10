import { Link, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import DisputesList from "./pages/DisputesList";
import Login from "./pages/Login";

export default function App() {
  const { session, logout } = useAuth();
  if (!session) {
    return (
      <Routes>
        <Route path="*" element={<Login />} />
      </Routes>
    );
  }
  return (
    <>
      <header className="topbar">
        <Link to="/" className="brand">Disputes console</Link>
        <div className="who">
          <span>{session.email}</span>
          <span className="role">{session.role === "agent" ? "Support agent" : "Customer"}</span>
          <button className="ghost" onClick={logout}>Sign out</button>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<DisputesList />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
