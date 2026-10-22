import type { Metadata } from "next";

import { MentorParticipantsWorkspace } from "./workspace";

export const metadata: Metadata = { title: "Rekap peserta" };

export default function MentorParticipantsPage() {
  return <MentorParticipantsWorkspace />;
}
