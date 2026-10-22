import type { Metadata } from "next";

import { ParticipantResultsWorkspace } from "./workspace";

export const metadata: Metadata = { title: "Hasil dan tindak lanjut" };

export default function ParticipantResultsPage() {
  return <ParticipantResultsWorkspace />;
}
