import type { Metadata } from "next";

import { SessionProposalWorkspace } from "./workspace";

export const metadata: Metadata = { title: "Ajukan sesi" };

export default function SessionProposalPage() {
  return <SessionProposalWorkspace />;
}
