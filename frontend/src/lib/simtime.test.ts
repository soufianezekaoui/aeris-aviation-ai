import { describe, expect, it } from "vitest";
import { formatOffset, formatSimUtc, scale, seekFromX } from "./simtime";

describe("formatOffset", () => {
  it("formats seconds as T+hh:mm:ss", () => {
    expect(formatOffset(0)).toBe("T+00:00:00");
    expect(formatOffset(160)).toBe("T+00:02:40");
    expect(formatOffset(3330)).toBe("T+00:55:30");
    expect(formatOffset(3661)).toBe("T+01:01:01");
  });
  it("never goes negative", () => {
    expect(formatOffset(-5)).toBe("T+00:00:00");
  });
});

describe("formatSimUtc", () => {
  it("keeps the simulated UTC time and says UTC", () => {
    expect(formatSimUtc("2030-01-01T08:02:40Z")).toBe("2030-01-01 08:02:40 UTC");
  });
  it("discloses a missing snapshot", () => {
    expect(formatSimUtc(null)).toBe("no snapshot");
  });
});

describe("seekFromX", () => {
  it("maps position to a time snapped to the sample interval", () => {
    expect(seekFromX(150, 50, 200, 1000, 5)).toBe(500);
    expect(seekFromX(51, 50, 200, 3330, 5)).toBe(15); // 0.005 * 3330 = 16.65 -> 15
  });
  it("clamps outside the plot and handles degenerate input", () => {
    expect(seekFromX(0, 50, 200, 1000, 5)).toBe(0);
    expect(seekFromX(999, 50, 200, 1000, 5)).toBe(1000);
    expect(seekFromX(100, 50, 0, 1000, 5)).toBe(0);
  });
});

describe("scale", () => {
  it("maps linearly and tolerates a flat range", () => {
    expect(scale(5, 0, 10, 0, 100)).toBe(50);
    expect(scale(5, 5, 5, 20, 80)).toBe(20);
  });
});
