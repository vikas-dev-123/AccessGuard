import { Link, useNavigate } from "react-router-dom";
import { api, RISK_ORDER, type Review } from "../api";
import { useAuth } from "../auth";
import { BarList } from "../components/BarList";
import { DownloadButtons } from "../components/DownloadButtons";
import { ReviewPicker } from "../components/ReviewPicker";
import { StatTile } from "../components/StatTile";
import { EmptyState, ErrorBanner, PageHeader, Spinner } from "../components/States";
import { fmtDate, fmtDateTime, systemLabel } from "../format";
import { useAsync, useReviewSelection } from "../hooks";

export default function DashboardPage() {
  const { user } = useAuth();
  const { reviews, selected, loading, error, reload, select } = useReviewSelection();

  if (loading && !reviews.length) return <Spinner label="Loading reviews" />;
  if (error) return <ErrorBanner error={error} onRetry={reload} />;
  if (!selected) {
    return (
      <EmptyState title="No access reviews yet">
        {user?.role === "auditor" ? (
          <>
            <p>Upload an HR master file and system user lists, then run the checks.</p>
            <Link to="/upload" className="btn btn-primary mt-4">Upload data</Link>
          </>
        ) : (
          <p>An auditor needs to upload data and run a review before results appear here.</p>
        )}
      </EmptyState>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        subtitle={<ReviewMeta review={selected} />}
        actions={
          <>
            {reviews.length > 1 && <ReviewPicker reviews={reviews} selected={selected} onSelect={select} />}
            <DownloadButtons reviewId={selected.id} />
          </>
        }
      />
      <ReviewSummary review={selected} />
    </div>
  );
}

function ReviewMeta({ review }: { review: Review }) {
  return (
    <span>
      Review #{review.id} · Data as of <strong className="font-medium text-ink">{fmtDate(review.as_of_date)}</strong>
      {" "}· Run by {review.run_by} on {fmtDateTime(review.run_at)} · {review.systems.map(systemLabel).join(", ")}
    </span>
  );
}

function ReviewSummary({ review }: { review: Review }) {
  const navigate = useNavigate();
  const summary = useAsync(() => api.summary(review.id), [review.id]);
  const checks = useAsync(api.checks, []);

  if (summary.error) return <ErrorBanner error={summary.error} onRetry={summary.reload} />;
  if (!summary.data) return <Spinner label="Loading summary" />;

  const s = summary.data;
  const findingsUrl = (params: Record<string, string>) =>
    `/findings?${new URLSearchParams({ review: String(review.id), ...params })}`;
  const codeByName = new Map((checks.data ?? []).map((c) => [c.name, c.code]));

  const byCheck = Object.entries(s.by_check)
    .map(([name, value]) => ({ key: codeByName.get(name) ?? name, label: name, value }))
    .sort((a, b) => b.value - a.value);
  const bySystem = Object.entries(s.by_system)
    .map(([system, value]) => ({ key: system, label: systemLabel(system), value }))
    .sort((a, b) => b.value - a.value);

  return (
    <>
      <section aria-label="Findings by risk" className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <div className="col-span-2 lg:col-span-1">
          <StatTile label="Total findings" value={s.total} hero to={findingsUrl({})}
            hint={`across ${review.systems.length} systems`} />
        </div>
        {RISK_ORDER.map((risk) => (
          <StatTile key={risk} label={risk} risk={risk} value={s.by_risk[risk] ?? 0}
            hint={s.total ? `${Math.round(((s.by_risk[risk] ?? 0) / s.total) * 100)}% of findings` : undefined}
            to={findingsUrl({ risk_rating: risk })} />
        ))}
      </section>

      <div className="grid gap-4 lg:grid-cols-5">
        <section className="card p-5 lg:col-span-3">
          <h2 className="font-semibold text-ink">Findings by check</h2>
          <p className="mb-4 text-sm text-muted">Select a check to see its findings</p>
          <BarList ariaLabel="Findings by check" data={byCheck}
            onSelect={(code) => navigate(findingsUrl({ check: code }))} />
        </section>
        <section className="card p-5 lg:col-span-2">
          <h2 className="font-semibold text-ink">Findings by system</h2>
          <p className="mb-4 text-sm text-muted">Cross-system SoD conflicts are listed separately</p>
          <BarList ariaLabel="Findings by system" data={bySystem}
            onSelect={(system) => navigate(findingsUrl({ system }))} />
        </section>
      </div>
    </>
  );
}
