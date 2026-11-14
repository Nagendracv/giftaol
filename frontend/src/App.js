import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { LangProvider } from "./lib/i18n";
import { AuthProvider } from "./lib/auth";
import { SiteProvider } from "./lib/site";
import Layout from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import AuthCallback from "./pages/AuthCallback";
import Dashboard from "./pages/Dashboard";
import NewGift from "./pages/NewGift";
import GiftDetail from "./pages/GiftDetail";
import Admin from "./pages/Admin";
import Legal, { NotFound } from "./pages/Legal";

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/gifts/new" element={<NewGift />} />
        <Route path="/gifts/:id" element={<ProtectedRoute><GiftDetail /></ProtectedRoute>} />
        <Route path="/admin" element={<ProtectedRoute admin><Admin /></ProtectedRoute>} />
        <Route path="/privacy" element={<Legal doc="privacy" />} />
        <Route path="/terms" element={<Legal doc="terms" />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <LangProvider>
      <AuthProvider>
        <SiteProvider>
          <BrowserRouter>
            <AppRouter />
          </BrowserRouter>
          <Toaster position="top-center" richColors />
        </SiteProvider>
      </AuthProvider>
    </LangProvider>
  );
}
