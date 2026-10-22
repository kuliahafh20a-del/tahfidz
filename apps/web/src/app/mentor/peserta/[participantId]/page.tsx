import type { Metadata } from "next";

import { MentorParticipantRecapWorkspace } from "./workspace";

export const metadata: Metadata = { title: "Riwayat peserta" };

export default async function MentorParticipantRecapPage({
  params,
}: {
  params: Promise<{ participantId: string }>;
}) {
  const { participantId } = await params;
  return <MentorParticipantRecapWorkspace enrollmentId={participantId} />;
}
