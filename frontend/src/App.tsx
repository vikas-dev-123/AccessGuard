import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { Layout } from "./components/Layout";
import { Spinner } from "./components/States";
import DashboardPage from "./pages/DashboardPage";
import FindingsPage from "./pages/FindingsPage";
import LoginPage from "./pages/LoginPage";
import UploadPage from "./pages/UploadPage";

export default function App() {
  const { user, loading } = useAuth();

  if (loading) return <Spinner label="Restoring session" />;
  if (!user) return <LoginPage />;

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="findings" element={<FindingsPage />} />
        <Route
          path="upload"
          element={user.role === "auditor" ? <UploadPage /> : <Navigate to="/dashboard" replace />}
        />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
