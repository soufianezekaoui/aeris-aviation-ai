import { SafetyIcon } from "./SafetyIcon";

/** Always visible (BR-08 / RULE-09). Yellow = caution. */
export function SimulationBanner() {
  return (
    <div role="note" className="border-b border-safety-yellow/40 bg-safety-yellow/10">
      <div className="mx-auto flex max-w-6xl items-start gap-3 px-4 py-2 text-sm">
        <span className="mt-0.5 shrink-0">
          <SafetyIcon kind="caution" size={18} />
        </span>
        <p className="text-safety-yellow">
          <strong className="uppercase tracking-wide">Educational simulation.</strong>{" "}
          <span className="text-white/85">
            AERIS is not a certified aviation system. Do not use it to operate an aircraft, replace
            approved manuals or checklists, or make real-world flight decisions.
          </span>
        </p>
      </div>
    </div>
  );
}
