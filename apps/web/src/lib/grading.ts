export type GradeComponent = {
  value: string | null;
  weight: string;
  status: "available" | "not_assessed" | "policy_pending" | "incomplete";
};

export type GradeSnapshot = {
  id: string;
  enrollment_id: string;
  status:
    | "incomplete"
    | "ready_for_exam"
    | "awaiting_exam"
    | "awaiting_components"
    | "graduated"
    | "not_graduated"
    | "needs_review";
  exam_readiness: "not_ready" | "ready_for_exam" | "exam_in_progress" | "exam_final";
  components: { k: GradeComponent; m: GradeComponent; d: GradeComponent };
  final_score: string | null;
  graduation_status: "graduated" | "not_graduated" | null;
  policy_version_id: string;
  policy_version: string;
  calculated_at: string;
  supersedes_id: string | null;
  missing_requirements: string[];
};

export type GradeHistory = { items: GradeSnapshot[] };

export const componentStatusLabel: Record<GradeComponent["status"], string> = {
  available: "Tersedia",
  not_assessed: "Belum dinilai",
  policy_pending: "Menunggu kebijakan",
  incomplete: "Belum lengkap",
};

export const missingRequirementLabel: Record<string, string> = {
  activity_44_themes_incomplete: "Nilai K belum mencakup seluruh 44 tema.",
  five_parts_not_enough: "Lima bagian belum seluruhnya berstatus Cukup.",
  mentor_aggregation_policy: "Agregasi nilai Mentor belum disahkan.",
  mentor_assessments_incomplete: "Penilaian Mentor belum lengkap.",
  final_exam: "Ujian Dosen belum final.",
  lecturer_component_unavailable: "Komponen D belum dapat dihitung.",
  grade_calculation_policy: "Kebijakan perhitungan nilai akhir belum disahkan.",
};
