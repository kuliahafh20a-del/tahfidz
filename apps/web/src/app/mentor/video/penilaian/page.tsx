import type { Metadata } from "next";

import { VideoAssessmentWorkspace } from "./workspace";

export const metadata: Metadata = { title: "Penilaian video · YAQin" };

export default function VideoAssessmentPage() {
  return <VideoAssessmentWorkspace />;
}
