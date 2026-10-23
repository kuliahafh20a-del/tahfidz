import type { Metadata } from "next";

import { ExamQueueWorkspace } from "./workspace";

export const metadata: Metadata = { title: "Antrean ujian · YAQin" };

export default function ExamQueuePage() {
  return <ExamQueueWorkspace />;
}
