import { describe, expect, it } from "vitest";

import { canRequestSession, targetsForPart, type Target } from "../lib/participant-calendar";

const activeTarget: Target = {
  id: "target-1",
  theme: {
    id: "theme-1",
    code: "T01",
    name: "An-Naba ayat 1-16",
    part_id: "part-1",
    part_no: 1,
    part_name: "Bagian 1",
  },
  initial_due_date: "2027-01-01",
  effective_due_date: "2027-01-01",
  status: "active",
  first_valid_submission_at: null,
  activity_score: null,
  locked_reason: null,
  allowed_actions: ["request_session"],
};

describe("participant calendar permissions", () => {
  it("renders session actions only from allowed_actions", () => {
    expect(canRequestSession(activeTarget)).toBe(true);
    expect(canRequestSession({ ...activeTarget, allowed_actions: [] })).toBe(false);
  });

  it("filters the 44-theme view by part", () => {
    const second = {
      ...activeTarget,
      id: "target-2",
      theme: { ...activeTarget.theme, id: "theme-2", part_id: "part-2", part_no: 2 },
    };
    expect(targetsForPart([activeTarget, second], "part-2")).toEqual([second]);
    expect(targetsForPart([activeTarget, second], null)).toHaveLength(2);
  });
});
