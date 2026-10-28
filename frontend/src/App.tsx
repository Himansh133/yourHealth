import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, RequireAuth } from "./auth";
import Layout from "./components/Layout";
import FamilyPage from "./pages/FamilyPage";
import LoginPage from "./pages/LoginPage";
import ProfilePage from "./pages/ProfilePage";
import ReviewPage from "./pages/ReviewPage";

function Private({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <Layout>{children}</Layout>
    </RequireAuth>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Private><FamilyPage /></Private>} />
          <Route path="/profiles/:pid" element={<Private><ProfilePage /></Private>} />
          <Route path="/profiles/:pid/trends" element={<Private><ProfilePage tab="trends" /></Private>} />
          <Route path="/profiles/:pid/medicines" element={<Private><ProfilePage tab="medicines" /></Private>} />
          <Route path="/documents/:did/review" element={<Private><ReviewPage /></Private>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
