import { createContext, useContext, useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { Show } from "@clerk/react";
import { useAuthedApi, errorText } from "@/lib/api";

const MeContext = createContext({ me: null, error: null });

function MeProvider() {
  const call = useAuthedApi();
  const [state, setState] = useState({ me: null, error: null });

  useEffect(() => {
    call({ url: "/me" })
      .then((r) => setState({ me: r.data, error: null }))
      .catch((e) => setState({ me: null, error: errorText(e) }));
  }, [call]);

  return (
    <MeContext.Provider value={state}>
      <Outlet />
    </MeContext.Provider>
  );
}

export function SignedInArea() {
  return (
    <>
      <Show when="signed-in"><MeProvider /></Show>
      <Show when="signed-out"><Navigate to="/sign-in" replace /></Show>
    </>
  );
}

export const useMe = () => useContext(MeContext);
