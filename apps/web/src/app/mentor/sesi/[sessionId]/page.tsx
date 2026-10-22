import type { Metadata } from "next";

import { ThemeAssessmentWorkspace } from "./workspace";

export const metadata: Metadata = { title: "Catatan pembimbingan" };

export default async function ThemeAssessmentPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  return <ThemeAssessmentWorkspace sessionId={sessionId} />;
}
