import { useState, type FormEvent } from "react";
import { useAuth } from "../auth";
import { Logo } from "../components/Logo";

const DEMO_USERS = [
  { username: "auditor", password: "Auditor@123", label: "Auditor", note: "upload, run reviews, view" },
  { username: "viewer", password: "Viewer@123", label: "Viewer", note: "view only" },
];

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(username, password);
    } catch (err) {
      setError((err as Error).message);
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <Logo className="size-12" />
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-ink">AccessGuard</h1>
            <p className="mt-1 text-sm text-ink-2">ITGC user access review for Apex Bank</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="card space-y-4 p-6">
          <div>
            <label htmlFor="username" className="label">Username</label>
            <input id="username" className="input" autoComplete="username" required
              value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div>
            <label htmlFor="password" className="label">Password</label>
            <input id="password" type="password" className="input" autoComplete="current-password" required
              value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {error && <p role="alert" className="text-sm text-danger">{error}</p>}
          <button type="submit" className="btn btn-primary w-full" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div className="mt-4 rounded-xl border border-dashed border-axis p-4">
          <p className="text-xs font-medium tracking-wide text-muted uppercase">Demo accounts</p>
          <div className="mt-2 space-y-1">
            {DEMO_USERS.map((u) => (
              <button key={u.username} type="button"
                onClick={() => { setUsername(u.username); setPassword(u.password); }}
                className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm hover:bg-surface-2">
                <span className="font-medium text-ink">{u.label}</span>
                <span className="text-xs text-muted">{u.note}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
