import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ChecklistsResponse, SimAlert, SimStateResponse } from "../types";
import { AlertList } from "./AlertList";
import { ChecklistPanel } from "./ChecklistPanel";
import { StatePanel } from "./StatePanel";

afterEach(cleanup);

const label = { synthetic: true as const, data_source: "synthetic simulation", disclaimer: "x" };

const alert = (over: Partial<SimAlert> = {}): SimAlert => ({
  id: 1, code: "TAKEOFF_CONFIG", level: "critical", message: "TAKEOFF CONFIG: flaps not at the briefed setting",
  t_start: 150, t_end: 230, start_time: "2030-01-01T08:02:30Z", end_time: "2030-01-01T08:03:50Z",
  active: true, ...over,
});

describe("AlertList", () => {
  it("labels the level in words, not just colour, and shows the raised time", () => {
    render(<AlertList alerts={[alert()]} emptyText="none" />);
    expect(screen.getByText(/Critical · TAKEOFF CONFIG/)).toBeTruthy();
    expect(screen.getByText(/raised T\+00:02:30/)).toBeTruthy();
  });
  it("marks cleared alerts and shows the empty text", () => {
    const { rerender } = render(<AlertList alerts={[alert({ active: false })]} emptyText="none" />);
    expect(screen.getByText("(cleared)")).toBeTruthy();
    rerender(<AlertList alerts={[]} emptyText="No simulated alert is active at this time." />);
    expect(screen.getByText("No simulated alert is active at this time.")).toBeTruthy();
  });
});

const state = (over: Partial<SimStateResponse> = {}): SimStateResponse => ({
  ...label, session_id: "abcdef12-0000-0000-0000-000000000000", scenario_id: "x", freshness: "exact",
  requested_t: 160, t_seconds: 160, snapshot_time: "2030-01-01T08:02:40Z", age_s: 0,
  generated_at: "2026-10-23T00:00:00Z",
  state: { phase: "TAKEOFF", altitude_ft: 0, airspeed_kt: 98.4, vertical_speed_fpm: 0, heading_deg: 90,
    flap_deg: 0, gear_down: true, n1_pct: 60, fuel_kg: 6400 },
  active_alerts: [], warnings: [], ...over,
});

describe("StatePanel (RULE-05)", () => {
  it("always shows the session id and the simulated snapshot time", () => {
    render(<StatePanel data={state()} />);
    expect(screen.getByText("abcdef12…")).toBeTruthy();
    expect(screen.getByText(/T\+00:02:40 · 2030-01-01 08:02:40 UTC/)).toBeTruthy();
    expect(screen.getByText("simulated clock", { exact: false })).toBeTruthy();
    expect(screen.getByText("DOWN")).toBeTruthy();
  });
  it("discloses a stale snapshot instead of presenting it as current", () => {
    render(<StatePanel data={state({ freshness: "stale", warnings: ["Requested t=99999s is past the end of the simulation (3330s)."] })} />);
    expect(screen.getByText("Stale")).toBeTruthy();
    expect(screen.getByText(/past the end of the simulation/)).toBeTruthy();
  });
  it("shows absent state as absent, with no invented values", () => {
    render(<StatePanel data={state({ freshness: "absent", state: null, t_seconds: null, snapshot_time: null,
      warnings: ["No state snapshot exists for this session at the requested time."] })} />);
    expect(screen.getByText("No snapshot")).toBeTruthy();
    expect(screen.queryByText("Altitude")).toBeNull();
  });
});

const checklists = (): ChecklistsResponse => ({
  ...label, session_id: "s", progress: { reviewed: 1, needs_attention: 0, total: 2 },
  semantics: "Review progress inside AERIS only. A status does not certify that any real-world procedure was performed.",
  checklists: [{ key: "k", title: "Departure review (generic training example)",
    progress: { reviewed: 1, needs_attention: 0, total: 2 },
    items: [
      { id: 7, position: 0, text: "Review the briefed takeoff flap setting", status: "reviewed", note: null, updated_at: "2026-10-23T00:00:00Z" },
      { id: 8, position: 1, text: "Review the landing gear indication", status: "not_reviewed", note: "check later", updated_at: "2026-10-23T00:00:00Z" },
    ] }],
});

describe("ChecklistPanel (RULE-07)", () => {
  it("always states that review status is not a real-world certification", () => {
    render(<ChecklistPanel data={checklists()} busy={new Set()} error={null} onUpdate={() => {}} />);
    expect(screen.getByText(/does not certify that any real-world procedure/)).toBeTruthy();
    expect(screen.getByText("1/2 reviewed", { selector: "p.font-mono.text-white\\/60" })).toBeTruthy();
  });
  it("records a status change for the right item and keeps its note", () => {
    const onUpdate = vi.fn();
    render(<ChecklistPanel data={checklists()} busy={new Set()} error={null} onUpdate={onUpdate} />);
    const group = screen.getByRole("group", { name: /Review the landing gear indication/ });
    fireEvent.click(group.querySelector("button:nth-child(3)")!); // Needs attention
    expect(onUpdate).toHaveBeenCalledWith(8, "needs_attention", "check later");
  });
  it("does not re-send the status that is already selected", () => {
    const onUpdate = vi.fn();
    render(<ChecklistPanel data={checklists()} busy={new Set()} error={null} onUpdate={onUpdate} />);
    const group = screen.getByRole("group", { name: /Review the briefed takeoff flap setting/ });
    fireEvent.click(group.querySelector("button[aria-pressed='true']")!);
    expect(onUpdate).not.toHaveBeenCalled();
  });
  it("shows a save error and disables the busy item", () => {
    render(<ChecklistPanel data={checklists()} busy={new Set([8])} error="Could not save." onUpdate={() => {}} />);
    expect(screen.getByRole("alert").textContent).toContain("Could not save.");
    const group = screen.getByRole("group", { name: /Review the landing gear indication/ });
    expect((group.querySelector("button") as HTMLButtonElement).disabled).toBe(true);
  });
});
