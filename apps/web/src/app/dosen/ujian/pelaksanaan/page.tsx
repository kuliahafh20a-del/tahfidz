import type { Metadata } from "next";

import { ExamListWorkspace } from "../exam-list-workspace";

export const metadata: Metadata = { title: "Pelaksanaan ujian · YAQin" };

export default function ExamExecutionListPage() {
  return <ExamListWorkspace mode="execution" />;
}
