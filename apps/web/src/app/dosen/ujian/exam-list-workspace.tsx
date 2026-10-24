"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell, PageHeader } from "@/components/shell";
import { Card, DataTable, FeedbackState, StatusBadge } from "@/components/ui";
import { Exam, examStatusLabel } from "@/lib/exams";
import { apiRequest, dateTimeLabel, SessionContext } from "@/lib/mentoring";

export function ExamListWorkspace({ mode }: { mode: "execution" | "summary" }) {
  const [context, setContext] = useState<SessionContext | null>(null);
  const [exams, setExams] = useState<Exam[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([
      apiRequest<SessionContext>("/auth/session"),
      apiRequest<Exam[]>("/lecturer/exams"),
    ])
      .then(([session, data]) => {
        setContext(session);
        setExams(data);
      })
      .catch((caught: unknown) =>
        setError(caught instanceof Error ? caught.message : "Daftar ujian tidak tersedia."),
      );
  }, []);

  const execution = mode === "execution";
  return (
    <AppShell
      accountName={context?.user.display_name ?? "Dosen"}
      initialRole="lecturer"
      organization={context?.active_context?.organization_name ?? "Program Tahfidz"}
    >
      <PageHeader
        breadcrumbs={[{ label: execution ? "Pelaksanaan ujian" : "Rekap ujian" }]}
        description={
          execution
            ? "Catat skor dan bukti setiap butir tanpa kehilangan draft."
            : "Tinjau status, kelengkapan, dan Nilai Ujian (Dosen) yang tersedia."
        }
        eyebrow={execution ? "D03 · Pelaksanaan ujian" : "D04 · Rekap ujian"}
        status={<StatusBadge tone="progress">{exams.length} ujian</StatusBadge>}
        title={execution ? "Pelaksanaan ujian" : "Rekap ujian"}
      />
      {error ? (
        <FeedbackState description={error} title="Data belum dapat dimuat" tone="error" />
      ) : null}
      {!error ? (
        <Card>
          <DataTable
            caption={execution ? "Daftar pelaksanaan ujian" : "Daftar rekap ujian"}
            headings={["Peserta", "Jadwal", "Status", "Nilai Ujian (Dosen)", "Tindakan"]}
            rows={exams.map((exam) => [
              `${exam.participant.display_name} · ${exam.participant.nim}`,
              dateTimeLabel(exam.scheduled_at),
              examStatusLabel[exam.status],
              exam.d_score ?? "Belum tersedia",
              <Link
                href={`/dosen/ujian/${exam.id}/${execution ? "pelaksanaan" : "rekap"}`}
                key={exam.id}
              >
                {execution ? "Buka pelaksanaan" : "Lihat rekap"}
              </Link>,
            ])}
          />
        </Card>
      ) : null}
    </AppShell>
  );
}
