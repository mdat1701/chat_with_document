import { useEffect, useRef } from "react";
import { Badge } from "@shared/ui";
import { track } from "@shared/analytics/client";
import { uiText } from "@shared/i18n/messages.vi";
import { formatCitation } from "./citations";
import type { CitationVM } from "./types";

const HOVER_VIEWED_THRESHOLD_MS = 500;

export type CitationChipProps = {
  citation: CitationVM;
  highlighted: boolean;
  showPageNumbers: boolean;
  onHighlight: (index: number | null) => void;
};

/**
 * Thẻ nguồn trong `CitationList` (T-306 §5.6, §5.7). Phát `citation_viewed`
 * khi hover ≥ 500ms hoặc khi nhấn (T-404 §3.2) — `props` chỉ gồm
 * `citation_index`, không chứa tên tệp (US-020).
 */
export function CitationChip({
  citation,
  highlighted,
  showPageNumbers,
  onHighlight,
}: CitationChipProps) {
  const hoverTimer = useRef<ReturnType<typeof setTimeout>>();
  const viewedRef = useRef(false);

  useEffect(
    () => () => {
      if (hoverTimer.current) clearTimeout(hoverTimer.current);
    },
    [],
  );

  const reportViewed = () => {
    if (viewedRef.current) return;
    viewedRef.current = true;
    track("citation_viewed", { citation_index: citation.index });
  };

  const handleMouseEnter = () => {
    onHighlight(citation.index);
    hoverTimer.current = setTimeout(reportViewed, HOVER_VIEWED_THRESHOLD_MS);
  };
  const clearHoverTimer = () => {
    if (hoverTimer.current) {
      clearTimeout(hoverTimer.current);
      hoverTimer.current = undefined;
    }
  };
  const handleMouseLeave = () => {
    onHighlight(null);
    clearHoverTimer();
  };
  const handleClick = () => {
    reportViewed();
  };

  const label = formatCitation(
    citation.documentName,
    citation.pageStart,
    citation.pageEnd,
    showPageNumbers,
  );

  return (
    <button
      type="button"
      className="chat-citation-chip"
      data-testid="citation-chip"
      data-highlighted={highlighted ? "true" : undefined}
      aria-label={uiText.citationLabel(citation.index, label)}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onFocus={() => onHighlight(citation.index)}
      onBlur={() => onHighlight(null)}
      onClick={handleClick}
    >
      <Badge tone={highlighted ? "info" : "neutral"}>
        [{citation.index}] 🗎 {label}
      </Badge>
    </button>
  );
}

export type CitationRefProps = {
  index: number;
  citation?: CitationVM;
  highlighted: boolean;
  onHighlight: (index: number | null) => void;
};

/**
 * Token `[n]` bên trong nội dung markdown (T-306 §5.5). Nếu `n` không khớp
 * thẻ nguồn nào → chữ thường, không tạo liên kết (IR-03).
 */
export function CitationRef({
  index,
  citation,
  highlighted,
  onHighlight,
}: CitationRefProps) {
  if (!citation) return <span>[{index}]</span>;
  return (
    <button
      type="button"
      className="chat-citation-ref"
      data-testid="citation-ref"
      data-highlighted={highlighted ? "true" : undefined}
      aria-label={`Xem nguồn ${index}`}
      onMouseEnter={() => onHighlight(index)}
      onMouseLeave={() => onHighlight(null)}
      onFocus={() => onHighlight(index)}
      onBlur={() => onHighlight(null)}
      onClick={() => onHighlight(index)}
    >
      [{index}]
    </button>
  );
}
