import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { SignIn, SignUp } from "@clerk/react";
import { api } from "@/lib/api";
import { useSite } from "@/lib/site";

function useSiteScript() {
  useEffect(() => {
    if (document.getElementById("aol-site-js")) return;
    const s = document.createElement("script");
    s.id = "aol-site-js";
    s.src = "/api/static/site.js";
    document.body.appendChild(s);
  }, []);
}

// Fallback for hosts where these paths are not routed to the server: shows the same server-rendered content.
function ServerContent({ url, params }) {
  const { site } = useSite();
  const [content, setContent] = useState(null);
  const query = params.toString();
  useSiteScript();
  useEffect(() => {
    api.get(`${url}?${query}`).then((r) => setContent(r.data)).catch(() => setContent({ html: "", css: "" }));
  }, [url, query, site.locale]);
  useEffect(() => { if (content) window.aolFocusShared?.(); }, [content]);
  if (!content) return null;
  return (
    <>
      <style>{content.css}</style>
      <div dangerouslySetInnerHTML={{ __html: content.html }} />
    </>
  );
}

export function HomePage() {
  const [params] = useSearchParams();
  return <ServerContent url="/home-content" params={params} />;
}

export function LegalPage({ kind }) {
  return <ServerContent url={`/legal/${kind}`} params={new URLSearchParams()} />;
}

export function AuthPage({ mode }) {
  return (
    <main className="flex justify-center px-4 py-12" data-testid={`${mode}-page`}>
      {mode === "sign-in" ? (
        <SignIn routing="path" path="/sign-in" signUpUrl="/sign-up" withSignUp />
      ) : (
        <SignUp routing="path" path="/sign-up" signInUrl="/sign-in" />
      )}
    </main>
  );
}
