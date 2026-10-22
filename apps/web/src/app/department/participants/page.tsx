import type { Metadata } from "next";

import { ParticipantAssignmentWorkspace } from "./workspace";

export const metadata: Metadata = {
  title: "Peserta dan penugasan",
};

export default function DepartmentParticipantsPage() {
  return <ParticipantAssignmentWorkspace />;
}
