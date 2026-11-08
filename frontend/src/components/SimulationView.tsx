import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  createSession,
  deleteSession,
  getChecklists,
  getScenarios,
  getSessions,
  getState,
  getTimeline,
  updateItem,
} from "../api";
import type {
  ChecklistsResponse,
  ReviewStatus,
  Scenario,
  SimSession,
  SimStateResponse,
  SimTimeline,
} from "../types";
import { AlertList } from "./AlertList";
import { ChecklistPanel } from "./ChecklistPanel";
import { ErrorPanel } from "./ErrorPanel";
import { SafetyIcon } from "./SafetyIcon";
import { SessionPicker } from "./SessionPicker";
import { SPEEDS, TimeControls } from "./TimeControls";
import { StatePanel } from "./StatePanel";
import { TimelineChart } from "./TimelineChart";

function Dashboard({ session, scenario }: { session: SimSession; scenario?: Scenario }) {
  const id = session.session_id;
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speedIdx, setSpeedIdx] = useState(1);
  const [state, setState] = useState<SimStateResponse | null>(null);
  const [timeline, setTimeline] = useState<SimTimeline | null>(null);
  const [checklists, setChecklists] = useState<ChecklistsResponse | null>(null);
  const [busy, setBusy] = useState<Set<number>>(new Set());
  const [error, setError] = useState<Error | null>(null);
  const [checkError, setCheckError] = useState<string | null>(null);

  // Timeline + checklists once per session.
  useEffect(() => {
    const ctl = new AbortController();
    Promise.all([getTimeline(id, 10, ctl.signal), getChecklists(id, ctl.signal)])
      .then(([tl, cl]) => {
        setTimeline(tl);
        setChecklists(cl);
      })
      .catch((e: Error) => e.name !== "AbortError" && setError(e));
    return () => ctl.abort();
  }, [id]);

  // State at the cursor. Debounced so scrubbing / playback does not flood the API.
  useEffect(() => {
    const ctl = new AbortController();
    const timer = setTimeout(() => {
      getState(id, t, ctl.signal)
        .then(setState)
        .catch((e: Error) => e.name !== "AbortError" && setError(e));
    }, 120);
    return () => {
      clearTimeout(timer);
      ctl.abort();
    };
  }, [id, t]);

  // Playback only moves the client-side cursor over generated data.
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => {
      setT((cur) => {
        const next = Math.min(session.duration_s, cur + SPEEDS[speedIdx].step);
        if (next >= session.duration_s) setPlaying(false);
        return next;
      });
    }, 500);
    return () => clearInterval(timer);
  }, [playing, speedIdx, session.duration_s]);

  const onPlaying = (p: boolean) => {
    if (p && t >= session.duration_s) setT(0); // "Replay"
    setPlaying(p);
  };

  const onUpdate = useCallback(
    async (itemId: number, status: ReviewStatus, note: string | null) => {
      setCheckError(null);
      setBusy((b) => new Set(b).add(itemId));
      try {
        await updateItem(id, itemId, { status, note });
        setChecklists(await getChecklists(id));
      } catch (e) {
        setCheckError(e instanceof ApiError ? e.message : "Could not save the review status.");
      } finally {
        setBusy((b) => {
          const next = new Set(b);
          next.delete(itemId);
          return next;
        });
      }
    },
    [id],
  );

  const activeIds = new Set((state?.active_alerts ?? []).map((a) => a.id));
  const history = (timeline?.alerts ?? []).filter((a) => a.t_start <= t && !activeIds.has(a.id));

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
      <div className="min-w-0 space-y-5">
        <header className="space-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-lg font-bold">{session.name}</h2>
            <span className="inline-flex items-center gap-1.5 rounded bg-safety-yellow px-2.5 py-1 text-[11px] font-extrabold uppercase text-navy-950">
              <SafetyIcon kind="caution" size={14} inverted />
              Simulated data · not live telemetry
            </span>
          </div>
          {scenario && (
            <p className="text-sm text-white/65">
              {scenario.learning_goal} <span className="text-white/40">· {scenario.aircraft}</span>
            </p>
          )}
        </header>

        {error && <ErrorPanel error={error} />}

        <TimeControls
          t={t}
          duration={session.duration_s}
          interval={session.sample_interval_s}
          playing={playing}
          speedIdx={speedIdx}
          onT={(v) => {
            setPlaying(false);
            setT(v);
          }}
          onPlaying={onPlaying}
          onSpeed={setSpeedIdx}
        />

        <StatePanel data={state} />

        {timeline && (
          <TimelineChart
            points={timeline.points}
            alerts={timeline.alerts}
            duration={session.duration_s}
            interval={session.sample_interval_s}
            t={t}
            onSeek={(v) => {
              setPlaying(false);
              setT(v);
            }}
          />
        )}

        <section aria-labelledby="alerts-heading" aria-live="polite" className="space-y-2">
          <h3 id="alerts-heading" className="text-xs font-bold uppercase tracking-widest text-safety-orange">
            Simulated alerts
          </h3>
          <AlertList alerts={state?.active_alerts ?? []} emptyText="No simulated alert is active at this time." />
          {history.length > 0 && (
            <>
              <p className="pt-1 text-[11px] uppercase tracking-widest text-white/40">Earlier in this session</p>
              <AlertList alerts={history.map((a) => ({ ...a, active: false }))} emptyText="" />
            </>
          )}
        </section>
      </div>

      <ChecklistPanel data={checklists} busy={busy} error={checkError} onUpdate={onUpdate} />
    </div>
  );
}

export function SimulationView() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [sessions, setSessions] = useState<SimSession[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [busy, setBusy] = useState(false);
  const selectedRef = useRef<string | null>(null);
  selectedRef.current = selected;

  const refresh = useCallback(async (pick?: string | null) => {
    const list = await getSessions();
    setSessions(list);
    const want = pick ?? selectedRef.current;
    setSelected(list.some((s) => s.session_id === want) ? want : (list[0]?.session_id ?? null));
  }, []);

  useEffect(() => {
    const ctl = new AbortController();
    getScenarios(ctl.signal)
      .then(setScenarios)
      .catch((e: Error) => e.name !== "AbortError" && setError(e));
    refresh().catch((e: Error) => setError(e));
    return () => ctl.abort();
  }, [refresh]);

  const act = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e as Error);
    } finally {
      setBusy(false);
    }
  };

  const session = sessions?.find((s) => s.session_id === selected) ?? null;

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8">
      {error && <ErrorPanel error={error} />}
      {sessions === null && !error && <p className="text-sm text-white/50">Loading sessions…</p>}
      {sessions && (
        <SessionPicker
          scenarios={scenarios}
          sessions={sessions}
          selected={selected}
          busy={busy}
          onSelect={setSelected}
          onCreate={(sid) =>
            act(async () => {
              const created = await createSession(sid);
              await refresh(created.session_id);
            })
          }
          onDelete={(sid) => {
            if (!window.confirm("Delete this session and its checklist progress?")) return;
            void act(async () => {
              await deleteSession(sid);
              await refresh(null);
            });
          }}
        />
      )}
      {session && (
        <Dashboard
          key={session.session_id}
          session={session}
          scenario={scenarios.find((s) => s.id === session.scenario_id)}
        />
      )}
    </div>
  );
}
