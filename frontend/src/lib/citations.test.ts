import { describe, expect, it } from "vitest";
import { splitCitations } from "./citations";

describe("splitCitations", () => {
  it("returns plain text untouched", () => {
    expect(splitCitations("No markers.")).toEqual([{ type: "text", value: "No markers." }]);
  });

  it("splits single, adjacent and grouped citations", () => {
    expect(splitCitations("A [1] B [2][3] C [1, 4].")).toEqual([
      { type: "text", value: "A " },
      { type: "cite", ids: [1] },
      { type: "text", value: " B " },
      { type: "cite", ids: [2] },
      { type: "cite", ids: [3] },
      { type: "text", value: " C " },
      { type: "cite", ids: [1, 4] },
      { type: "text", value: "." },
    ]);
  });

  it("ignores brackets that are not citations", () => {
    expect(splitCitations("see [Figure 2] and [x]")).toEqual([
      { type: "text", value: "see [Figure 2] and [x]" },
    ]);
  });

  it("handles a leading citation and empty input", () => {
    expect(splitCitations("[2] starts")[0]).toEqual({ type: "cite", ids: [2] });
    expect(splitCitations("")).toEqual([]);
  });
});
