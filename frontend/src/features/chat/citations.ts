import { uiText } from "@shared/i18n/messages.vi";

export function formatCitationPage(
  start?: number | null,
  end?: number | null,
): string | null {
  if (start == null) return null;
  // TODO(DQ-07): confirm multi-page citation format with Tech Lead.
  const prefix = uiText.citationPagePrefix;
  return start === end || end == null
    ? `${prefix} ${start}`
    : `${prefix} ${start}–${end}`;
}

export function formatCitation(
  name: string,
  start?: number | null,
  end?: number | null,
  enabled = true,
) {
  if (!enabled) return name;
  const page = formatCitationPage(start, end);
  return page ? `${name} · ${page}` : name;
}
