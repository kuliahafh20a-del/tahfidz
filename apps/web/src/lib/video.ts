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
