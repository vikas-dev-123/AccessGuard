import { useState } from "react";
import { fmtNumber } from "../format";

export interface Bar {
  key: string;
  label: string;
  value: number;
}

interface Props {
  data: Bar[];
  ariaLabel: string;
  onSelect?: (key: string) => void;
}

/** Single-series horizontal bars: one hue, value at the tip, per-bar hover readout. */
export function BarList({ data, ariaLabel, onSelect }: Props) {
  const [active, setActive] = useState<string | null>(null);
  const max = Math.max(1, ...data.map((d) => d.value));
  const total = data.reduce((sum, d) => sum + d.value, 0);

  return (
    <ul aria-label={ariaLabel} className="space-y-1.5" onMouseLeave={() => setActive(null)}>
      {data.map((d) => {
        const share = total ? Math.round((d.value / total) * 100) : 0;
        const fraction = d.value / max;
        const dimmed = active !== null && active !== d.key;
        const row = (
          <>
            <span className="truncate text-left text-sm text-ink-2" title={d.label}>
              {d.label}
            </span>
            <span className="flex min-w-0 items-center gap-2">
              <span
                className="h-4 rounded-r-[4px] bg-series-1 transition-opacity"
                style={{
                  width: `calc((100% - 3rem) * ${fraction})`,
                  minWidth: d.value > 0 ? 2 : 0,
                  opacity: dimmed ? 0.4 : 1,
                }}
              />
              <span className="text-sm font-medium tabular-nums text-ink">{fmtNumber(d.value)}</span>
            </span>
            {active === d.key && (
              <span
                role="tooltip"
                className="pointer-events-none absolute right-0 -top-8 z-10 rounded-md border border-line bg-surface px-2 py-1 text-xs whitespace-nowrap text-ink shadow-md"
              >
                {d.label}: <strong>{fmtNumber(d.value)}</strong> findings ({share}% of total)
              </span>
            )}
          </>
        );
        const rowClass =
          "relative grid w-full grid-cols-1 items-center gap-x-3 gap-y-0.5 rounded-md px-2 py-1.5 sm:grid-cols-[15rem_1fr]";
        return (
          <li key={d.key} onMouseEnter={() => setActive(d.key)}>
            {onSelect ? (
              <button
                type="button"
                onClick={() => onSelect(d.key)}
                onFocus={() => setActive(d.key)}
                onBlur={() => setActive(null)}
                aria-label={`${d.label}: ${d.value} findings, ${share}% of total. Show these findings.`}
                className={`${rowClass} cursor-pointer hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-accent`}
              >
                {row}
              </button>
            ) : (
              <div className={rowClass}>{row}</div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
