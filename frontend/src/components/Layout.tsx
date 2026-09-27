import { NavLink, Outlet, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth";
import { Logo } from "./Logo";

export function Layout() {
  const { user, logout } = useAuth();
  const [params] = useSearchParams();
  const review = params.get("review");
  const keepReview = review ? `?review=${review}` : "";

  const links = [
    { to: "/dashboard", label: "Dashboard", search: keepReview },
    { to: "/findings", label: "Findings", search: keepReview },
    ...(user?.role === "auditor" ? [{ to: "/upload", label: "Upload & run", search: "" }] : []),
  ];

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <div className="flex items-center gap-2.5">
            <Logo />
            <div className="leading-tight">
              <div className="font-semibold text-ink">AccessGuard</div>
              <div className="text-xs text-muted">Apex Bank · User access review</div>
            </div>
          </div>
          <nav aria-label="Main" className="order-3 flex w-full gap-1 overflow-x-auto sm:order-none sm:w-auto">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={{ pathname: l.to, search: l.search }}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 text-sm font-medium whitespace-nowrap transition-colors ${
                    isActive ? "bg-accent-wash/60 text-ink" : "text-ink-2 hover:bg-surface-2 hover:text-ink"
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <div className="text-right leading-tight">
              <div className="text-sm font-medium text-ink">{user?.full_name}</div>
              <div className="text-xs text-muted capitalize">{user?.role}</div>
            </div>
            <button type="button" onClick={logout} className="btn btn-secondary py-1.5">
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:py-8">
        <Outlet />
      </main>
    </div>
  );
}
