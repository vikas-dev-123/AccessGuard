import { Link } from "react-router-dom";
import type { RiskRating } from "../api";
import { fmtNumber } from "../format";
import { RiskDot } from "./Risk";

interface Props {
  label: string;
  value: number;
  hint?: string;
  risk?: RiskRating;
  hero?: boolean;
  to?: string;
}

export function StatTile({ label, value, hint, risk, hero, to }: Props) {
  const body = (
    <>
      <div className="flex items-center gap-2 text-sm text-ink-2">
        {risk && <RiskDot risk={risk} />}
        {label}
      </div>
      <div className={`mt-2 font-semibold tracking-tight text-ink ${hero ? "text-5xl" : "text-3xl"}`}>
        {fmtNumber(value)}
      </div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </>
  );
  const base = "card block p-5";
  if (!to) return <div className={base}>{body}</div>;
  return (
    <Link
      to={to}
      className={`${base} transition-colors hover:border-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent`}
    >
      {body}
    </Link>
  );
}
