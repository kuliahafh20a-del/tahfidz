import type { Metadata } from "next";

import { ExamPackageWorkspace } from "./workspace";

export const metadata: Metadata = { title: "Paket soal · YAQin" };

export default async function ExamPackagePage({ params }: { params: Promise<{ examId: string }> }) {
  const { examId } = await params;
  return <ExamPackageWorkspace examId={examId} />;
}
