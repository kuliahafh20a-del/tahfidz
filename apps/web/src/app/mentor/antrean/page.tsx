import type { Metadata } from "next";

import { MentorQueueWorkspace } from "./workspace";

export const metadata: Metadata = { title: "Binaan dan antrean" };

export default function MentorQueuePage() {
  return <MentorQueueWorkspace />;
}
