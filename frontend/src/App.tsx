import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { accountHome, AuthProvider, RequireAuth, useAuth } from "./auth";
import type { AccountType } from "./api/types";
import Layout from "./components/Layout";
import DemoPage from "./pages/DemoPage";
import EvaluationPage from "./pages/EvaluationPage";
import FamilyPage from "./pages/FamilyPage";
import LoginPage from "./pages/LoginPage";
import ProfilePage from "./pages/ProfilePage";
import PublicSharePage from "./pages/PublicSharePage";
import ReviewPage from "./pages/ReviewPage";
import WhatsAppPage from "./pages/WhatsAppPage";
import DoctorRegisterPage from "./pages/DoctorRegisterPage";
import DoctorHomePage from "./pages/DoctorHomePage";
import AdminDoctorsPage from "./pages/AdminDoctorsPage";

function Private({ children, accountType = "patient" }: { children: ReactNode; accountType?: AccountType }) {
  return (
    <RequireAuth accountType={accountType}>
      <Layout>{children}</Layout>
    </RequireAuth>
  );
}

function Home() {
  const { user } = useAuth();
  if (user && user.account_type !== "patient") return <Navigate to={accountHome(user.account_type)} replace />;
  return <Private><FamilyPage /></Private>;
}

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Home />} />
          <Route path="/demo" element={<Private><DemoPage /></Private>} />
          <Route path="/evaluation" element={<Private><EvaluationPage /></Private>} />
          <Route path="/doctor/register" element={<DoctorRegisterPage />} />
          <Route path="/doctor" element={<Private accountType="doctor"><DoctorHomePage /></Private>} />
          <Route path="/profiles/:pid/allergies" element={<Private><ProfilePage tab="allergies" /></Private>} />
          <Route path="/profiles/:pid/access" element={<Private><ProfilePage tab="access" /></Private>} />
          <Route path="/admin/doctors" element={<Private accountType="admin"><AdminDoctorsPage /></Private>} />
          <Route path="/profiles/:pid" element={<Private><ProfilePage /></Private>} />
          <Route path="/profiles/:pid/reports" element={<Private><ProfilePage tab="reports" /></Private>} />
          <Route path="/profiles/:pid/compare" element={<Private><ProfilePage tab="compare" /></Private>} />
          <Route path="/profiles/:pid/trends" element={<Private><ProfilePage tab="trends" /></Private>} />
          <Route path="/profiles/:pid/medicines" element={<Private><ProfilePage tab="medicines" /></Private>} />
          <Route path="/profiles/:pid/ask" element={<Private><ProfilePage tab="ask" /></Private>} />
          <Route path="/profiles/:pid/sheet" element={<Private><ProfilePage tab="sheet" /></Private>} />
          <Route path="/s/:token" element={<PublicSharePage />} />
          <Route path="/settings/whatsapp" element={<Private><WhatsAppPage /></Private>} />
          <Route path="/documents/:did/review" element={<Private><ReviewPage /></Private>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
