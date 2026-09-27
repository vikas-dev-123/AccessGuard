import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, RISK_ORDER, type Finding, type Review } from "../api";
import { DownloadButtons } from "../components/DownloadButtons";
import { ReviewPicker } from "../components/ReviewPicker";
import { RiskBadge } from "../components/Risk";
import { EmptyState, ErrorBanner, PageHeader, Spinner } from "../components/States";
import { fmtNumber, systemLabel } from "../format";
import { useAsync, useReviewSelection } from "../hooks";

const PAGE_SIZE = 25;
const FILTER_KEYS = ["system", "check", "risk_rating", "q"] as const;

export default function FindingsPage() {
  const { reviews, selected, loading, error, reload, select } = useReviewSelection();

  if (loading && !reviews.length) return <Spinner label="Loading reviews" />;
  if (error) return <ErrorBanner error={error} onRetry={reload} />;
  if (!selected) return <EmptyState title="No access reviews yet">Run a review to see findings here.</EmptyState>;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Findings"
        subtitle={`Review #${selected.id} · ${fmtNumber(selected.total_findings)} findings in total`}
        actions={
          <>
            {reviews.length > 1 && <ReviewPicker reviews={reviews} selected={selected} onSelect={select} />}
            <DownloadButtons reviewId={selected.id} />
          </>
        }
      />
      <FindingsTable review={selected} />
    </div>
  );
}

function FindingsTable({ review }: { review: Review }) {
  const [params, setParams] = useSearchParams();
  const system = params.get("system") ?? "";
  const check = params.get("check") ?? "";
  const risk = params.get("risk_rating") ?? "";
  const query = params.get("q") ?? "";
  const page = Math.max(1, Number(params.get("page")) || 1);

  const [searchInput, setSearchInput] = useState(query);
  const checks = useAsync(api.checks, []);

  function update(changes: Partial<Record<(typeof FILTER_KEYS)[number] | "page", string>>) {
    setParams((p) => {
      for (const [key, value] of Object.entries(changes)) {
        if (value) p.set(key, value);
        else p.delete(key);
      }
      if (!("page" in changes)) p.delete("page");
      return p;
    }, { replace: true });
  }

  // setSearchParams' updater sees the params of the render that created it, so the debounced
  // call must go through a ref to the latest update() or it would undo newer filter changes.
  const updateRef = useRef(update);
  updateRef.current = update;

  useEffect(() => setSearchInput(query), [query]);
  useEffect(() => {
    if (searchInput.trim() === query) return;
    const timer = setTimeout(() => updateRef.current({ q: searchInput.trim() }), 300);
    return () => clearTimeout(timer);
  }, [searchInput, query]);

  const findings = useAsync(
    () => api.findings(review.id, {
      system, check, risk_rating: risk, search: query,
      limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE,
    }),
    [review.id, system, check, risk, query, page],
  );

  const hasFilters = Boolean(system || check || risk || query);
  const total = findings.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const first = total ? (page - 1) * PAGE_SIZE + 1 : 0;
  const last = Math.min(page * PAGE_SIZE, total);

  return (
    <section className="card">
      <div className="grid gap-3 border-b border-line p-4 sm:grid-cols-2 lg:grid-cols-[1fr_auto_auto_auto_auto]">
        <label className="sm:col-span-2 lg:col-span-1">
          <span className="sr-only">Search findings</span>
          <input type="search" className="input" placeholder="Search username, employee ID, details…"
            value={searchInput} onChange={(e) => setSearchInput(e.target.value)} />
        </label>
        <FilterSelect label="Risk" value={risk} onChange={(v) => update({ risk_rating: v })}
          options={RISK_ORDER.map((r) => ({ value: r, label: r }))} />
        <FilterSelect label="Check" value={check} onChange={(v) => update({ check: v })}
          options={(checks.data ?? []).map((c) => ({ value: c.code, label: c.name }))} />
        <FilterSelect label="System" value={system} onChange={(v) => update({ system: v })}
          options={review.systems.map((s) => ({ value: s, label: systemLabel(s) }))} />
        <button type="button" className="btn btn-secondary" disabled={!hasFilters}
          onClick={() => { setSearchInput(""); update({ system: "", check: "", risk_rating: "", q: "" }); }}>
          Clear
        </button>
      </div>

      {findings.error && <div className="p-4"><ErrorBanner error={findings.error} onRetry={findings.reload} /></div>}

      {!findings.data && !findings.error ? (
        <Spinner label="Loading findings" />
      ) : findings.data && findings.data.items.length === 0 ? (
        <p className="px-4 py-16 text-center text-sm text-ink-2">
          No findings match these filters.
        </p>
      ) : findings.data && (
        <div className={`transition-opacity ${findings.loading ? "opacity-60" : ""}`}>
          <ul className="divide-y divide-line md:hidden">
            {findings.data.items.map((f) => <FindingCard key={f.finding_id} finding={f} />)}
          </ul>
          <div className="hidden overflow-x-auto md:block">
          <table className="w-full min-w-[56rem] text-left text-sm">
            <thead className="border-b border-line text-xs tracking-wide text-muted uppercase">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">ID</th>
                <th scope="col" className="px-4 py-3 font-medium">Risk</th>
                <th scope="col" className="px-4 py-3 font-medium">Check</th>
                <th scope="col" className="px-4 py-3 font-medium">System</th>
                <th scope="col" className="px-4 py-3 font-medium">Employee</th>
                <th scope="col" className="px-4 py-3 font-medium">Username</th>
                <th scope="col" className="px-4 py-3 font-medium">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {findings.data.items.map((f) => <FindingRow key={f.finding_id} finding={f} />)}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {total > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-4 py-3 text-sm text-ink-2">
          <span>Showing {fmtNumber(first)}–{fmtNumber(last)} of {fmtNumber(total)}</span>
          <div className="flex items-center gap-2">
            <button type="button" className="btn btn-secondary py-1.5" disabled={page <= 1}
              onClick={() => update({ page: String(page - 1) })}>Previous</button>
            <span className="tabular-nums">Page {page} of {pages}</span>
            <button type="button" className="btn btn-secondary py-1.5" disabled={page >= pages}
              onClick={() => update({ page: String(page + 1) })}>Next</button>
          </div>
        </div>
      )}
    </section>
  );
}

function FindingRow({ finding: f }: { finding: Finding }) {
  return (
    <tr className="align-top hover:bg-surface-2/60">
      <td className="px-4 py-3 font-mono text-xs whitespace-nowrap text-ink-2">{f.finding_id}</td>
      <td className="px-4 py-3"><RiskBadge risk={f.risk_rating} /></td>
      <td className="px-4 py-3 text-ink">{f.check_name}</td>
      <td className="px-4 py-3 text-ink-2">{systemLabel(f.system)}</td>
      <td className="px-4 py-3 font-mono text-xs whitespace-nowrap text-ink-2">{f.employee_id ?? "—"}</td>
      <td className="px-4 py-3 font-mono text-xs text-ink">
        {f.username.split(", ").map((u) => <div key={u} className="break-words">{u}</div>)}
      </td>
      <td className="min-w-[22rem] px-4 py-3 text-ink-2">{f.details}</td>
    </tr>
  );
}

function FindingCard({ finding: f }: { finding: Finding }) {
  return (
    <li className="space-y-2 px-4 py-4">
      <div className="flex items-center justify-between gap-2">
        <RiskBadge risk={f.risk_rating} />
        <span className="font-mono text-xs text-muted">{f.finding_id}</span>
      </div>
      <div>
        <div className="text-sm font-medium text-ink">{f.check_name}</div>
        <div className="text-xs text-ink-2">
          {systemLabel(f.system)} · {f.employee_id ?? "No employee ID"} ·{" "}
          <span className="font-mono break-words">{f.username}</span>
        </div>
      </div>
      <p className="text-sm text-ink-2">{f.details}</p>
    </li>
  );
}

interface FilterSelectProps {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}

function FilterSelect({ label, value, options, onChange }: FilterSelectProps) {
  return (
    <label>
      <span className="sr-only">{label}</span>
      <select className="input lg:w-auto" value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">All {label.toLowerCase()}s</option>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}
