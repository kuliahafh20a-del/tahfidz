import type { Metadata } from "next";

import { ParticipantWorkspace } from "../participant-workspace";

export const metadata: Metadata = { title: "Target dan kalender" };

export default function ParticipantTargetsPage() {
  return <ParticipantWorkspace view="targets" />;
}
