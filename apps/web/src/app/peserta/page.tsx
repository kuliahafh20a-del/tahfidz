import type { Metadata } from "next";

import { ParticipantWorkspace } from "./participant-workspace";

export const metadata: Metadata = { title: "Beranda peserta" };

export default function ParticipantDashboardPage() {
  return <ParticipantWorkspace view="dashboard" />;
}
