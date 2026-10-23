import type { Metadata } from "next";

import { VideoEligibilityWorkspace } from "./workspace";

export const metadata: Metadata = { title: "Kelayakan video" };

export default function MentorVideoEligibilityPage() {
  return <VideoEligibilityWorkspace />;
}
