import "@/App.css";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import ClerkAuthProvider from "@/components/auth/ClerkAuthProvider";
import { SiteLayout } from "@/components/SiteLayout";
import { SiteProvider } from "@/lib/site";
import { SignedInArea } from "@/lib/me";
import { AuthPage, HomePage, LegalPage } from "@/pages/PublicPages";
import Insights from "@/pages/admin/Insights";
import Dashboard from "@/pages/Dashboard";
import AdminLayout from "@/pages/admin/AdminLayout";
import AccessLogs from "@/pages/admin/AccessLogs";
import SiteConfig from "@/pages/admin/SiteConfig";
import Texts from "@/pages/admin/Texts";
import Users from "@/pages/admin/Users";
import Gifts from "@/pages/admin/Gifts";
import GiftForm from "@/pages/gift/GiftForm";
import GiftCheckout from "@/pages/gift/GiftCheckout";
import { GiftDetail } from "@/pages/MyGifts";

function App() {
  return (
    <BrowserRouter>
      <ClerkAuthProvider>
        <SiteProvider>
          <Routes>
            <Route element={<SiteLayout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/privacy" element={<LegalPage kind="privacy" />} />
              <Route path="/terms" element={<LegalPage kind="terms" />} />
              <Route path="/sign-in/*" element={<AuthPage mode="sign-in" />} />
              <Route path="/sign-up/*" element={<AuthPage mode="sign-up" />} />
              <Route path="/gift" element={<GiftForm />} />
              <Route path="/gift/:checkoutId" element={<GiftCheckout />} />
              <Route element={<SignedInArea />}>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/gifts/:giftId" element={<GiftDetail />} />
                <Route path="/admin" element={<AdminLayout />}>
                  <Route index element={<Navigate to="logs" replace />} />
                  <Route path="logs" element={<AccessLogs />} />
                  <Route path="insights" element={<Insights />} />
                  <Route path="sites" element={<SiteConfig />} />
                  <Route path="texts" element={<Texts />} />
                  <Route path="users" element={<Users />} />
                  <Route path="gifts" element={<Gifts />} />
                </Route>
              </Route>
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Route>
          </Routes>
        </SiteProvider>
      </ClerkAuthProvider>
      <Toaster position="bottom-right" richColors />
    </BrowserRouter>
  );
}

export default App;
