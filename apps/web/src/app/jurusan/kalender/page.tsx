import type { Metadata } from "next";

import { DepartmentCalendarWorkspace } from "./workspace";

export const metadata: Metadata = {
  title: "Kalender angkatan",
};

export default function DepartmentCalendarPage() {
  return <DepartmentCalendarWorkspace />;
}
