"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell, PageHeader, SupportPanel, WorkSupportLayout } from "@/components/shell";
import { Card, DataTable, FeedbackState, StatusBadge } from "@/components/ui";
import { ExamSummary, questionKindLabel } from "@/lib/exams";
import { apiRequest, dateTimeLabel, SessionContext } from "@/lib/mentoring";

import styles from "../exam-workspace.module.css";

export function ExamSummaryWorkspace({ examId }: { examId: string }) {
  const [context, setContext] = useState<SessionContext | null>(null);
  const [summary, setSummary] = useState<ExamSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([
      apiRequest<SessionContext>("/auth/session"),
      apiRequest<ExamSummary>(`/exams/${examId}/summary`),
    ])
      .then(([session, loaded]) => {
        setContext(session);
        setSummary(loaded);
      })
      .catch((caught: unknown) =>
        setError(caught instanceof Error ? caught.message : "Rekap tidak tersedia."),
      );
  }, [examId]);

  const exam = summary?.exam;
  return (
    <AppShell
      accountName={context?.user.display_name ?? "Dosen"}
      initialRole="lecturer"
      organization={context?.active_context?.organization_name ?? "Program Tahfidz"}
    >
      <PageHeader
        breadcrumbs={[
          { href: "/dosen/ujian/rekap", label: "Rekap ujian" },
          { label: exam?.participant.display_name ?? "Ujian" },
        ]}
        description="Nilai D hanya ditampilkan setelah seluruh butir, bukti, dan kebijakan agregasi tervalidasi."
        eyebrow="D04 · Rekap ujian"
        status={
          <StatusBadge tone={summary?.d_status === "available" ? "success" : "warning"}>
            {summary?.d_status === "available" ? "Nilai tersedia" : "Menunggu kebijakan"}
          </StatusBadge>
        }
        title={exam ? `Rekap ${exam.participant.display_name}` : "Rekap ujian"}
      />
      {error ? (
        <FeedbackState description={error} title="Rekap belum dapat dimuat" tone="error" />
      ) : null}
      {!error && !summary ? (
        <FeedbackState
          description="Mengambil ringkasan penilaian."
          title="Memuat rekap"
          tone="loading"
        />
      ) : null}
      {summary && exam ? (
        <WorkSupportLayout
          support={
            <>
              <SupportPanel title="Nilai D">
                <p className={styles.score}>{exam.d_score ?? "—"}</p>
                <p className={styles.muted}>
                  {summary.d_status === "available"
                    ? `Agregasi ${exam.package_policy.aggregation_method}`
                    : "Tidak dihitung sebelum DEC-002 disahkan."}
                </p>
              </SupportPanel>
              <SupportPanel title="Kelengkapan">
                <p className={styles.muted}>
                  {summary.assessed_item_count} dari {summary.total_item_count} butir dinilai.
                </p>
                {summary.missing_requirements.length ? (
                  <ul className={styles.list}>
                    {summary.missing_requirements.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : null}
              </SupportPanel>
            </>
          }
        >
          <Card title="Ringkasan peserta">
            <dl className={styles.details}>
              <div>
                <dt>Peserta</dt>
                <dd>
                  {exam.participant.display_name} · {exam.participant.nim}
                </dd>
              </div>
              <div>
                <dt>Pelaksanaan</dt>
                <dd>{dateTimeLabel(exam.actual_at ?? exam.scheduled_at)}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>{exam.status}</dd>
              </div>
              <div>
                <dt>Versi kebijakan</dt>
                <dd>{exam.policy_version}</dd>
              </div>
            </dl>
          </Card>
          <Card title="Penilaian per butir">
            <DataTable
              caption="Nilai dan bukti setiap butir ujian"
              headings={["Butir", "Jenis", "Skor", "Catatan", "Bukti"]}
              rows={exam.items.map((item) => {
                const assessment = exam.assessments.find((entry) => entry.exam_item_id === item.id);
                return [
                  item.sequence_no,
                  questionKindLabel[item.kind],
                  assessment?.manual_score ?? "—",
                  assessment?.notes ?? "—",
                  assessment?.incidents.map((incident) => incident.location_text).join(", ") || "—",
                ];
              })}
            />
          </Card>
          <Card title="Bukti final">
            <p className={styles.muted}>
              {exam.evidence_media_ids.length
                ? exam.evidence_media_ids.join(", ")
                : "Belum ada media bukti final."}
            </p>
            <div className={styles.actions}>
              <Link href={`/dosen/ujian/${exam.id}/pelaksanaan`}>Kembali ke pelaksanaan</Link>
            </div>
          </Card>
        </WorkSupportLayout>
      ) : null}
    </AppShell>
  );
}
