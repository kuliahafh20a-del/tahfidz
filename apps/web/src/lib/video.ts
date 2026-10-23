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
