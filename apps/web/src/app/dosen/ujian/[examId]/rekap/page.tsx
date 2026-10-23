import type { Metadata } from "next";

import { ExamSummaryWorkspace } from "./workspace";

export const metadata: Metadata = { title: "Rekap ujian · YAQin" };

export default async function ExamSummaryPage({ params }: { params: Promise<{ examId: string }> }) {
  const { examId } = await params;
  return <ExamSummaryWorkspace examId={examId} />;
}
