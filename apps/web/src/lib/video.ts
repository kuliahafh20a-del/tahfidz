export type VideoAttemptStatus = "open" | "submitted" | "under_review" | "finalized" | "closed";

export type VideoVersionStatus = "submitted" | "available" | "failed" | "replaced";

export type VideoVersion = {
  id: string;
  version_no: number;
  video_url: string;
  recorded_on: string;
  submitted_at: string;
  status: VideoVersionStatus;
};

export type VideoAttempt = {
  id: string;
  enrollment_id: string;
  part_id: string;
  part_no: number;
  part_name: string;
  cycle_no: number;
  revision_no: number;
  status: VideoAttemptStatus;
  row_version: number;
  versions: VideoVersion[];
  allowed_actions: string[];
};

export type EligibilityDecision = "eligible" | "ineligible";
export type EligibilityReviewStatus = "draft" | "final" | "superseded";

export type EligibilityCheck = {
  code: string;
  passed: boolean;
  note: string | null;
};

export type EligibilityReview = {
  id: string;
  reviewer_id: string;
  checklist_version: string;
  decision: EligibilityDecision | null;
  reason: string | null;
  status: EligibilityReviewStatus;
  finalized_at: string | null;
  row_version: number;
  checks: EligibilityCheck[];
};

export type VideoEligibility = {
  video_version_id: string;
  attempt_id: string;
  participant: {
    enrollment_id: string;
    user_id: string;
    display_name: string;
    nim: string;
  };
  part_id: string;
  part_no: number;
  part_name: string;
  cycle_no: number;
  revision_no: number;
  video_version_no: number;
  video_url: string;
  recorded_on: string;
  submitted_at: string;
  video_status: VideoVersionStatus;
  checklist_version: string;
  criteria: Array<{ code: string; label: string; required: boolean }>;
  review: EligibilityReview | null;
  allowed_actions: string[];
};

export type VideoAssessmentOutcome = "enough" | "not_enough";

export type VideoAssessmentIncident = {
  id: string;
  location_text: string;
  video_second: number | null;
  primary_category: string;
  context: string | null;
  assistance: "none" | "cue" | "answer";
  self_corrected: boolean;
  counted: boolean;
  counting_reason: string | null;
  note: string | null;
};

export type VideoAssessment = {
  assessment_id: string;
  video_version_id: string;
  eligibility_review_id: string;
  participant: VideoEligibility["participant"];
  part_id: string;
  part_no: number;
  part_name: string;
  cycle_no: number;
  revision_no: number;
  video_version_no: number;
  video_url: string;
  status: "draft" | "final" | "superseded" | "needs_review";
  manual_score: number | null;
  mentor_note: string | null;
  counted_errors: number;
  outcome: VideoAssessmentOutcome | null;
  incidents: VideoAssessmentIncident[];
  feedback_audio: {
    id: string;
    file_name: string;
    status:
      | "uploading"
      | "pending_validation"
      | "validating"
      | "available"
      | "failed"
      | "quarantined"
      | "deleted";
  } | null;
  actual_at: string;
  finalized_at: string | null;
  policy_version_id: string;
  policy_version: string;
  row_version: number;
  allowed_actions: string[];
};

export const videoOutcomeLabel: Record<VideoAssessmentOutcome, string> = {
  enough: "Cukup",
  not_enough: "Belum Cukup",
};
