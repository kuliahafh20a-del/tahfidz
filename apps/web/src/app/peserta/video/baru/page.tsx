import type { Metadata } from "next";

import { VideoSubmissionWorkspace } from "./workspace";

export const metadata: Metadata = { title: "Kirim video bagian" };

export default function ParticipantVideoSubmissionPage() {
  return <VideoSubmissionWorkspace />;
}
