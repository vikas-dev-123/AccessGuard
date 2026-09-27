import type { RiskRating } from "../api";

const DOT_CLASS: Record<RiskRating, string> = {
  High: "bg-risk-high",
  Medium: "bg-risk-medium",
  Low: "bg-risk-low",
  Informational: "bg-risk-info",
};

export function RiskDot({ risk }: { risk: RiskRating }) {
  return <span aria-hidden="true" className={`inline-block size-2.5 shrink-0 rounded-full ${DOT_CLASS[risk]}`} />;
}

/** Status colour always travels with its text label, never alone. */
export function RiskBadge({ risk }: { risk: RiskRating }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface-2 px-2 py-0.5 text-xs font-medium whitespace-nowrap text-ink">
      <RiskDot risk={risk} />
      {risk}
    </span>
  );
}
