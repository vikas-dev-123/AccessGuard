const SYSTEM_LABELS: Record<string, string> = {
  core_banking: "Core banking",
  loan_system: "Loan system",
  database: "Database",
};

export function systemLabel(system: string): string {
  return system
    .split(" + ")
    .map((s) => SYSTEM_LABELS[s] ?? s.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase()))
    .join(" + ");
}

const dateFormat = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" });
const dateTimeFormat = new Intl.DateTimeFormat("en-GB", {
  day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
});

/** Formats a YYYY-MM-DD date without shifting it through UTC. */
export function fmtDate(isoDate: string): string {
  const [y, m, d] = isoDate.slice(0, 10).split("-").map(Number);
  return dateFormat.format(new Date(y, m - 1, d));
}

export function fmtDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso));
}

export function todayIso(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export function fmtNumber(n: number): string {
  return n.toLocaleString("en-US");
}

export function fmtBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
