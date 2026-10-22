import type { StatusTone } from "@/components/ui";

import type { SessionContext } from "@/lib/mentoring";

export type AssessmentStatus = "draft" | "final" | "superseded" | "needs_review";
export type ThemeOutcome = "enough" | "repeat" | "follow_up";
export type AssistanceType = "none" | "cue" | "answer";

export type AssessmentIncident = {
  id: string;
  location_text: string;
  video_second: number | null;
  primary_category: string;
  context: string | null;
  assistance: AssistanceType;
  self_corrected: boolean;
  counted: boolean;
  counting_reason: string | null;
  note: string | null;
};

export type ThemeAssessment = {
  assessment_id: string;
  session_id: string;
  session_theme_id: string;
  participant: {
    enrollment_id: string;
    user_id: string;
    display_name: string;
    nim: string;
  };
  theme: {
    id: string;
    theme_id: string;
    code: string;
    name: string;
    part_id: string;
    part_no: number;
    part_name: string;
  };
  status: AssessmentStatus;
  attempt_no: number;
  outcome: ThemeOutcome | null;
  manual_score: number | null;
  actual_at: string;
  finalized_at: string | null;
  mentor_note: string | null;
  incidents: AssessmentIncident[];
  counted_incidents: number;
  policy_version_id: string;
  policy_version: string;
  row_version: number;
  allowed_actions: string[];
};

export type MentorParticipant = {
  enrollment_id: string;
  user_id: string;
  display_name: string;
  nim: string;
  final_assessments: number;
  enough_themes: number;
  follow_up_themes: number;
  allowed_actions: string[];
};

export type IncidentDraft = {
  location_text: string;
  primary_category: string;
  context: string;
  assistance: AssistanceType;
  self_corrected: boolean;
  counted: boolean;
  counting_reason: string;
  note: string;
};

export type { SessionContext };

export const assessmentStatusLabel: Record<AssessmentStatus, string> = {
  draft: "Draft",
  final: "Final",
  superseded: "Digantikan",
  needs_review: "Perlu ditinjau",
};

export const outcomeLabel: Record<ThemeOutcome, string> = {
  enough: "Cukup",
  repeat: "Ulangi",
  follow_up: "Tindak lanjut",
};

export function assessmentTone(status: AssessmentStatus): StatusTone {
  if (status === "final") return "success";
  if (status === "draft") return "progress";
  if (status === "needs_review") return "warning";
  return "neutral";
}

export function outcomeTone(outcome: ThemeOutcome | null): StatusTone {
  if (outcome === "enough") return "success";
  if (outcome === "follow_up") return "warning";
  if (outcome === "repeat") return "danger";
  return "neutral";
}

export function emptyIncident(): IncidentDraft {
  return {
    location_text: "",
    primary_category: "tajwid",
    context: "",
    assistance: "none",
    self_corrected: false,
    counted: true,
    counting_reason: "",
    note: "",
  };
}
