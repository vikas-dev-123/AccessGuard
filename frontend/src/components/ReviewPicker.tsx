import type { Review } from "../api";
import { fmtDate } from "../format";

interface Props {
  reviews: Review[];
  selected: Review;
  onSelect: (id: number) => void;
}

export function ReviewPicker({ reviews, selected, onSelect }: Props) {
  return (
    <label className="flex items-center gap-2 text-sm text-ink-2">
      <span className="shrink-0">Review</span>
      <select
        className="input w-auto py-1.5"
        value={selected.id}
        onChange={(e) => onSelect(Number(e.target.value))}
      >
        {reviews.map((r) => (
          <option key={r.id} value={r.id}>
            #{r.id} · as of {fmtDate(r.as_of_date)}
          </option>
        ))}
      </select>
    </label>
  );
}
