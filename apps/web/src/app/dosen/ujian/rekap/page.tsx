import type { Metadata } from "next";

import { ExamListWorkspace } from "../exam-list-workspace";

export const metadata: Metadata = { title: "Rekap ujian · YAQin" };

export default function ExamSummaryListPage() {
  return <ExamListWorkspace mode="summary" />;
}
