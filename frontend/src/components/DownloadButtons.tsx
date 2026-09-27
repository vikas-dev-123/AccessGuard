import { useState } from "react";
import { api } from "../api";

type Kind = "excel" | "pdf";

export function DownloadButtons({ reviewId }: { reviewId: number }) {
  const [busy, setBusy] = useState<Kind | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handle(kind: Kind) {
    setBusy(kind);
    setError(null);
    try {
      await api.downloadReport(reviewId, kind);
    } catch (e) {
      setError(`Could not download the ${kind === "excel" ? "Excel" : "PDF"} report: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex gap-2">
        <button type="button" className="btn btn-secondary" disabled={busy !== null} onClick={() => handle("excel")}>
          <DownloadIcon />
          {busy === "excel" ? "Preparing…" : "Excel report"}
        </button>
        <button type="button" className="btn btn-primary" disabled={busy !== null} onClick={() => handle("pdf")}>
          <DownloadIcon />
          {busy === "pdf" ? "Preparing…" : "PDF report"}
        </button>
      </div>
      {error && (
        <p role="alert" className="text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

function DownloadIcon() {
  return (
    <svg viewBox="0 0 20 20" className="size-4" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path strokeLinecap="round" strokeLinejoin="round" d="M10 3v10m0 0-4-4m4 4 4-4M4 16h12" />
    </svg>
  );
}
