import type { Metadata } from "next";

import { DashboardShowcase } from "./dashboard-showcase";

export const metadata: Metadata = {
  title: "Beranda",
};

export default function HomePage() {
  return <DashboardShowcase />;
}
