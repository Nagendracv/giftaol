import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { useLang } from "../lib/i18n";

export const Loading = () => {
  const { t } = useLang();
  return <div className="py-24 text-center text-stone-500" data-testid="page-loading" role="status">{t("common.loading")}</div>;
};

export const ProtectedRoute = ({ children, admin = false }) => {
  const { user } = useAuth();
  const location = useLocation();
  if (user === null) return <Loading />;
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />;
  if (admin && !user.is_admin) return <Navigate to="/dashboard" replace />;
  return children;
};
