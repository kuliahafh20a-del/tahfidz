import type { Metadata } from "next";

import { ExamExecutionWorkspace } from "./workspace";

export const metadata: Metadata = { title: "Pelaksanaan ujian · YAQin" };

export default async function ExamExecutionPage({
  params,
}: {
  params: Promise<{ examId: string }>;
}) {
  const { examId } = await params;
  return <ExamExecutionWorkspace examId={examId} />;
}
