export type Segment =
  | { type: "text"; value: string }
  | { type: "cite"; ids: number[] };

const CITE = /\[(\d+(?:\s*,\s*\d+)*)\]/g;

/** Split an answer into plain text and `[n]` / `[n, m]` citation markers. */
export function splitCitations(text: string): Segment[] {
  const out: Segment[] = [];
  let last = 0;
  for (const m of text.matchAll(CITE)) {
    const start = m.index ?? 0;
    if (start > last) out.push({ type: "text", value: text.slice(last, start) });
    out.push({ type: "cite", ids: m[1].split(",").map((n) => Number(n.trim())) });
    last = start + m[0].length;
  }
  if (last < text.length) out.push({ type: "text", value: text.slice(last) });
  return out;
}
