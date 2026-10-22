import type { Metadata } from "next";

import { AuthCard } from "../auth-card";

export const metadata: Metadata = { title: "Pulihkan akun" };

export default function RecoveryPage() {
  return <AuthCard mode="recovery" />;
}
