import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { api, errMsg } from "../lib/api";
import { Loading } from "../components/ProtectedRoute";

export default function AuthCallback() {
  const location = useLocation();
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const done = useRef(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (done.current) return;
    done.current = true;
    const match = location.hash.match(/session_id=([^&]+)/);
    const sessionId = match ? decodeURIComponent(match[1]) : "";
    const next = sessionStorage.getItem("giftaol_next") || "/dashboard";
    sessionStorage.removeItem("giftaol_next");
    window.history.replaceState(null, "", window.location.pathname);
    api.post("/auth/google", { session_id: sessionId })
      .then(({ data }) => {
        setUser(data);
        navigate(next.startsWith("/") ? next : "/dashboard", { replace: true });
      })
      .catch((e) => {
        toast.error(errMsg(e));
        setUser(false);
        navigate("/login", { replace: true });
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return error ? <p role="alert" className="p-8 text-red-800">{error}</p> : <Loading />;
}
