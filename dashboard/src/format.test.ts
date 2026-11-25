import { describe, expect, it } from "vitest";
import { compact, formatDay, percent, shortId, summarizeRedactions } from "./format";
import { describeRule } from "./ruleLabels";

describe("format", () => {
  it("compacts numbers like 1,284 / 12.9K / 4.2M", () => {
    expect(compact(0)).toBe("0");
    expect(compact(1284)).toBe("1,284");
    expect(compact(12900)).toBe("12.9K");
    expect(compact(4_200_000)).toBe("4.2M");
  });

  it("formats a percentage, or a dash when there is nothing to divide by", () => {
    expect(percent(1, 8)).toBe("12.5%");
    expect(percent(213, 1284)).toBe("16.6%");
    expect(percent(0, 0)).toBe("—");
  });

  it("shortens ids to 8 characters", () => {
    expect(shortId("12345678-aaaa-bbbb")).toBe("12345678");
  });

  it("formats an ISO day without timezone drift", () => {
    expect(formatDay("2026-11-20")).toBe("Nov 20");
    expect(formatDay("2026-01-01")).toBe("Jan 1");
  });

  it("summarises redaction counts", () => {
    expect(summarizeRedactions({ PAN: 1, PHONE: 2 })).toBe("PAN ×1, PHONE ×2");
    expect(summarizeRedactions({})).toBe("None");
  });

  it("describes known rules and falls back to the raw id", () => {
    expect(describeRule("INJ_IGNORE_PREVIOUS")).toMatch(/ignore/i);
    expect(describeRule("SOME_NEW_RULE")).toBe("SOME_NEW_RULE");
  });
});
