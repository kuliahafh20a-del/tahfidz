export type TargetStatus = "scheduled" | "active" | "completed" | "closed";

export type Target = Readonly<{
  id: string;
  theme: {
    id: string;
    code: string;
    name: string;
    part_id: string;
    part_no: number;
    part_name: string;
  };
  initial_due_date: string;
  effective_due_date: string;
  status: TargetStatus;
  first_valid_submission_at: string | null;
  activity_score: number | null;
  locked_reason: string | null;
  allowed_actions: string[];
}>;

export type PartProgress = Readonly<{
  id: string;
  part_no: number;
  name: string;
  total_targets: number;
  completed_targets: number;
  status: "active" | "completed" | "locked";
  locked_reason: string | null;
}>;

export type Progress = Readonly<{
  total_targets: number;
  completed_targets: number;
  overdue_targets: number;
  expected_completed_targets: number;
  completion_percentage: number;
  on_track: boolean;
  projected_completion_date: string | null;
  active_part: PartProgress | null;
  parts: PartProgress[];
}>;

export type Dashboard = Readonly<{
  participant: {
    id: string;
    display_name: string;
    enrollment_id: string;
    cohort_name: string;
    cohort_start_date: string;
    cohort_close_date: string | null;
  };
  progress: Progress;
  next_target: Target | null;
  upcoming_targets: Target[];
}>;

export function canRequestSession(target: Target): boolean {
  return target.allowed_actions.includes("request_session");
}

export function targetsForPart(targets: readonly Target[], partId: string | null): Target[] {
  return partId === null
    ? [...targets]
    : targets.filter((target) => target.theme.part_id === partId);
}
