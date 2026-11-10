import { describe, expect, it } from "vitest";
import { parseSSEChunk } from "./api";

describe("parseSSEChunk", () => {
  it("parses complete events and keeps partial frames", () => {
    const buf =
      'data: {"type":"status","stage":"searching"}\n\n' +
      'data: {"type":"answer","patient_response":"hi"}\n\n' +
      'data: {"type":"d';
    const { events, rest } = parseSSEChunk(buf);
    expect(events).toHaveLength(2);
    expect(events[0]).toEqual({ type: "status", stage: "searching" });
    expect(rest).toBe('data: {"type":"d');
  });

  it("skips malformed frames without throwing", () => {
    const { events } = parseSSEChunk('data: not-json\n\ndata: {"type":"done"}\n\n');
    expect(events).toHaveLength(1);
  });

  it("returns empty events for heartbeat-only chunks", () => {
    const { events, rest } = parseSSEChunk("\n\n");
    expect(events).toHaveLength(0);
    expect(rest).toBe("");
  });
});
