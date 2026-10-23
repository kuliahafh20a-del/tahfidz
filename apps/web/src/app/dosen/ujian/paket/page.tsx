import Link from "next/link";

import { AppShell, PageHeader } from "@/components/shell";
import { Card } from "@/components/ui";

export default function ExamPackageEntryPage() {
  return (
    <AppShell accountName="Dosen" initialRole="lecturer" organization="Program Tahfidz">
      <PageHeader
        breadcrumbs={[{ href: "/dosen/ujian", label: "Antrean ujian" }, { label: "Paket soal" }]}
        description="Paket soal selalu dibuka dari peserta yang telah memenuhi syarat."
        eyebrow="D02 · Paket soal"
        title="Pilih peserta terlebih dahulu"
      />
      <Card title="Buka dari antrean">
        <p>
          Pilih peserta Siap Ujian agar paket soal terikat pada enrollment dan policy version yang
          benar.
        </p>
        <Link href="/dosen/ujian">Kembali ke antrean ujian</Link>
      </Card>
    </AppShell>
  );
}
