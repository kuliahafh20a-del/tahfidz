export type QuestionKind = "continue_verses" | "surah_order" | "recitation";
export type QuestionSource = "application" | "lecturer";
export type ExamStatus = "draft" | "scheduled" | "in_progress" | "final" | "cancelled";

export type QuestionVersion = {
  id: string;
  question_key: string;
  author_id: string | null;
  source: QuestionSource;
  kind: QuestionKind;
  stimulus: string;
  answer_reference: Record<string, unknown>;
  scope: Record<string, unknown>;
  version_no: number;
  status: "draft" | "verified" | "inactive";
};

export type ExamQueueItem = {
  participant: {
    enrollment_id: string;
    user_id: string;
    display_name: string;
    nim: string;
  };
  completed_parts: number;
  required_parts: number;
  latest_exam_id: string | null;
  latest_exam_status: ExamStatus | null;
  allowed_actions: string[];
};

export type ExamItem = {
  id: string;
  sequence_no: number;
  question_version_id: string;
  source: QuestionSource;
  kind: QuestionKind;
  stimulus: string;
  scope: Record<string, unknown>;
  answer_reference: Record<string, unknown>;
  question_version_no: number;
  weight: string | null;
};

export type Exam = {
  id: string;
  participant: ExamQueueItem["participant"];
  lecturer_id: string;
  policy_version_id: string;
  policy_version: string;
  scheduled_at: string;
  actual_at: string | null;
  lecturer_note: string | null;
  status: ExamStatus;
  items: ExamItem[];
  package_policy: {
    approved: boolean;
    required_item_count: number | null;
    expected_total_weight: string | null;
    blockers: string[];
  };
  row_version: number;
  finalized_at: string | null;
  allowed_actions: string[];
};

export const examStatusLabel: Record<ExamStatus, string> = {
  draft: "Draft paket",
  scheduled: "Terjadwal",
  in_progress: "Berlangsung",
  final: "Final",
  cancelled: "Dibatalkan",
};

export const questionKindLabel: Record<QuestionKind, string> = {
  continue_verses: "Sambung ayat",
  surah_order: "Urutan surah",
  recitation: "Tilawah",
};
