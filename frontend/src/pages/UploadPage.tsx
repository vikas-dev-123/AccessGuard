import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError, type Dataset } from "../api";
import { PageHeader } from "../components/States";
import { fmtBytes, fmtDateTime, fmtNumber, systemLabel, todayIso } from "../format";
import { useAsync } from "../hooks";

type Field = "hr_file" | "core_banking_file" | "loan_system_file" | "database_file";

const HR_COLUMNS = "employee_id, name, department, designation, status, joining_date, termination_date";
const ACCOUNT_COLUMNS =
  "user_id, employee_id, username, role, account_status, created_date, last_login_date, status_last_updated";

const SLOTS: { field: Field; title: string; example: string; columns: string; required?: boolean }[] = [
  { field: "hr_file", title: "HR master", example: "hr_employees.csv", columns: HR_COLUMNS, required: true },
  { field: "core_banking_file", title: "Core banking users", example: "core_banking_users.csv", columns: ACCOUNT_COLUMNS },
  { field: "loan_system_file", title: "Loan system users", example: "loan_system_users.csv", columns: ACCOUNT_COLUMNS },
  { field: "database_file", title: "Database users", example: "database_users.csv", columns: ACCOUNT_COLUMNS },
];

export default function UploadPage() {
  const [files, setFiles] = useState<Partial<Record<Field, File>>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [uploaded, setUploaded] = useState<Dataset | null>(null);
  const datasets = useAsync(api.datasets, [uploaded?.id]);

  const hasSystemFile = SLOTS.some((s) => !s.required && files[s.field]);
  const ready = Boolean(files.hr_file) && hasSystemFile;

  function setFile(field: Field, file: File | null) {
    setFiles((prev) => {
      const next = { ...prev };
      if (file) next[field] = file;
      else delete next[field];
      return next;
    });
    setError(null);
  }

  async function handleUpload(e: FormEvent) {
    e.preventDefault();
    const form = new FormData();
    for (const [field, file] of Object.entries(files)) form.append(field, file);
    setSubmitting(true);
    setError(null);
    setUploaded(null);
    try {
      setUploaded(await api.upload(form));
      setFiles({});
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, (err as Error).message));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Upload & run"
        subtitle="Upload the HR master and at least one system user list. Every file is validated before anything is stored."
      />

      <form onSubmit={handleUpload} className="card space-y-5 p-5">
        <h2 className="font-semibold text-ink">1. Upload data</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {SLOTS.map((slot) => (
            <FileSlot key={slot.field} {...slot} file={files[slot.field] ?? null}
              onChange={(f) => setFile(slot.field, f)} />
          ))}
        </div>

        {error && <UploadErrors error={error} />}
        {uploaded && (
          <div role="status" className="rounded-lg border border-line bg-surface-2 px-4 py-3 text-sm">
            <p className="font-medium text-ink">
              <span className="text-success">✓</span> Dataset #{uploaded.id} uploaded and validated
            </p>
            <p className="mt-1 text-ink-2">
              {fmtNumber(uploaded.hr_employee_count)} employees ·{" "}
              {Object.entries(uploaded.account_counts)
                .map(([s, n]) => `${fmtNumber(n)} ${systemLabel(s).toLowerCase()} accounts`).join(" · ")}
            </p>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-muted">
            {ready ? "Ready to validate." : "Add the HR master and at least one system file."} CSV (UTF-8), max 10 MB each, dates as YYYY-MM-DD.
          </p>
          <button type="submit" className="btn btn-primary" disabled={!ready || submitting}>
            {submitting ? "Validating…" : "Upload & validate"}
          </button>
        </div>
      </form>

      <RunReviewPanel datasets={datasets.data ?? []} />
    </div>
  );
}

interface FileSlotProps {
  field: Field;
  title: string;
  example: string;
  columns: string;
  required?: boolean;
  file: File | null;
  onChange: (file: File | null) => void;
}

function FileSlot({ field, title, example, columns, required, file, onChange }: FileSlotProps) {
  const [dragging, setDragging] = useState(false);
  const inputId = `file-${field}`;

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const dropped = e.dataTransfer.files[0];
        if (dropped) onChange(dropped);
      }}
      className={`rounded-lg border border-dashed p-4 transition-colors ${
        dragging ? "border-accent bg-accent-wash/30" : file ? "border-line bg-surface-2/50" : "border-axis"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-ink">
            {title}{" "}
            {required
              ? <span className="font-normal text-danger">(required)</span>
              : <span className="font-normal text-muted">(optional)</span>}
          </h3>
          <p className="mt-0.5 text-xs text-muted">e.g. {example}</p>
        </div>
        <label htmlFor={inputId} className="btn btn-secondary shrink-0 cursor-pointer py-1.5">
          {file ? "Replace" : "Choose file"}
        </label>
        <input id={inputId} type="file" accept=".csv,text/csv" className="sr-only"
          onChange={(e) => {
            const chosen = e.target.files?.[0];
            if (chosen) onChange(chosen);
            e.target.value = "";
          }} />
      </div>
      {file ? (
        <div className="mt-3 flex items-center gap-3 rounded-md border border-line bg-surface px-3 py-2 text-sm">
          <span className="min-w-0 flex-1 truncate font-medium text-ink">{file.name}</span>
          <span className="shrink-0 text-xs text-muted">{fmtBytes(file.size)}</span>
          <button type="button" onClick={() => onChange(null)}
            className="shrink-0 text-xs font-medium text-ink-2 underline-offset-2 hover:text-ink hover:underline">
            Remove
          </button>
        </div>
      ) : (
        <p className="mt-3 text-xs text-ink-2">
          Drop a CSV here or choose a file. Columns: <span className="break-words font-mono">{columns}</span>
        </p>
      )}
    </div>
  );
}

function UploadErrors({ error }: { error: ApiError }) {
  return (
    <div role="alert" className="rounded-lg border border-risk-high/40 bg-risk-high/5 p-4 text-sm">
      <p className="font-medium text-ink">{error.message}</p>
      {error.errors && (
        <ul className="mt-2 list-disc space-y-1 pl-5">
          {error.errors.map((e, i) => (
            <li key={i}>
              {e.file && <span className="font-mono text-xs font-medium text-ink">{e.file}: </span>}
              <span className="text-ink-2">{e.error}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function RunReviewPanel({ datasets }: { datasets: Dataset[] }) {
  const navigate = useNavigate();
  const [chosen, setChosen] = useState<number | null>(null);
  const [asOf, setAsOf] = useState(todayIso());
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const datasetId = chosen ?? datasets[0]?.id ?? null;

  async function run(e: FormEvent) {
    e.preventDefault();
    if (datasetId === null) return;
    setRunning(true);
    setError(null);
    try {
      const review = await api.runReview({ dataset_id: datasetId, as_of_date: asOf });
      navigate(`/dashboard?review=${review.id}`);
    } catch (err) {
      setError((err as Error).message);
      setRunning(false);
    }
  }

  return (
    <form onSubmit={run} className="card space-y-4 p-5">
      <div>
        <h2 className="font-semibold text-ink">2. Run access review</h2>
        <p className="mt-1 text-sm text-ink-2">
          Runs all seven checks against a dataset and saves the results as a new review.
        </p>
      </div>
      {datasets.length === 0 ? (
        <p className="text-sm text-muted">Upload a dataset first.</p>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="dataset" className="label">Dataset</label>
              <select id="dataset" className="input" value={datasetId ?? ""}
                onChange={(e) => setChosen(Number(e.target.value))}>
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    #{d.id} · {fmtDateTime(d.uploaded_at)} · {d.hr_employee_count} employees, {d.systems.length} systems
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="as-of" className="label">Data extracted on (as-of date)</label>
              <input id="as-of" type="date" className="input" required value={asOf}
                onChange={(e) => setAsOf(e.target.value)} />
              <p className="mt-1 text-xs text-muted">Dormancy is measured back from this date.</p>
            </div>
          </div>
          {error && <p role="alert" className="text-sm text-danger">{error}</p>}
          <div className="flex justify-end">
            <button type="submit" className="btn btn-primary" disabled={running || datasetId === null}>
              {running ? "Running checks…" : "Run review"}
            </button>
          </div>
        </>
      )}
    </form>
  );
}
