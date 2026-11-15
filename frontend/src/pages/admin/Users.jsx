import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { useAuthedApi, errorText } from "@/lib/api";
import { useMe } from "@/lib/me";
import { AdminTitle } from "@/pages/admin/AdminLayout";

export default function Users() {
  const call = useAuthedApi();
  const { me } = useMe();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    call({ url: "/users" }).then((r) => setData(r.data)).catch((e) => setError(errorText(e)));
  }, [call]);
  useEffect(load, [load]);

  const setRole = async (user, role) => {
    try {
      await call({ url: `/users/${user.user_id}/role`, method: "patch", data: { role } });
      toast.success(`${user.email || user.user_id} is now ${role}`);
      load();
    } catch (e) { toast.error(errorText(e)); }
  };

  if (!data) return <p className="text-stone-500">{error || "Loading…"}</p>;
  return (
    <div data-testid="users-page">
      <AdminTitle title="Users & admins" />
      <p className="mb-4 text-sm text-stone-600">People appear here after their first sign-in. At least one admin always remains.</p>
      <div className="overflow-x-auto rounded-xl border border-stone-200 bg-white">
        <table className="w-full text-left text-sm" data-testid="users-table">
          <thead className="bg-stone-100 text-xs uppercase tracking-wider text-stone-700">
            <tr>{["Email", "Joined", "Role"].map((h) => <th key={h} scope="col" className="px-3 py-2.5">{h}</th>)}</tr>
          </thead>
          <tbody>
            {data.users.map((u) => (
              <tr key={u.user_id} className="border-b border-stone-100 hover:bg-stone-50" data-testid="users-row">
                <td className="px-3 py-2">{u.email || u.user_id}{u.user_id === me?.user_id && <span className="ml-2 text-xs text-stone-500">(you)</span>}</td>
                <td className="px-3 py-2">{u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}</td>
                <td className="px-3 py-2">
                  <select value={u.role} onChange={(e) => setRole(u, e.target.value)} aria-label={`Role for ${u.email || u.user_id}`}
                    className="field" data-testid={`promote-demote-user-${u.user_id}`}>
                    {data.roles.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
