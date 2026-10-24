"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell, PageHeader, SupportPanel, WorkSupportLayout } from "@/components/shell";
import { Button, Card, FeedbackState, StatusBadge } from "@/components/ui";
import { VideoAssessmentCard } from "@/components/video-assessment-card";
import {
  assessmentStatusLabel,
  assessmentTone,
  MentorParticipant,
  outcomeLabel,
  outcomeTone,
  ThemeAssessment,
} from "@/lib/assessments";
import { apiRequest, CursorPage, dateTimeLabel, SessionContext } from "@/lib/mentoring";
import { VideoAssessment } from "@/lib/video";

import styles from "./workspace.module.css";

export function MentorParticipantRecapWorkspace({ enrollmentId }: { enrollmentId: string }) {
  const [context, setContext] = useState<SessionContext | null>(null);
  const [participant, setParticipant] = useState<MentorParticipant | null>(null);
  const [history, setHistory] = useState<ThemeAssessment[]>([]);
  const [videoHistory, setVideoHistory] = useState<VideoAssessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    void Promise.all([
      apiRequest<SessionContext>("/auth/session"),
      apiRequest<MentorParticipant>(`/mentor/participants/${enrollmentId}`),
      apiRequest<CursorPage<ThemeAssessment>>(
        `/enrollments/${enrollmentId}/assessment-history?limit=100`,
      ),
      apiRequest<VideoAssessment[]>(`/enrollments/${enrollmentId}/video-assessment-history`),
    ])
      .then(([loadedContext, loadedParticipant, page, loadedVideoHistory]) => {
        if (!active) return;
        setContext(loadedContext);
        setParticipant(loadedParticipant);
        setHistory(page.items);
        setVideoHistory(loadedVideoHistory);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof Error ? caught.message : "Rekap tidak tersedia.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [enrollmentId, reloadKey]);

  return (
    <AppShell
      accountName={context?.user.display_name ?? "Mentor"}
      initialRole="mentor"
      organization={context?.active_context?.organization_name ?? "Program Tahfidz"}
    >
      <PageHeader
        breadcrumbs={[
          { href: "/mentor/peserta", label: "Rekap peserta" },
          { label: participant?.display_name ?? "Riwayat" },
        ]}
        description="Riwayat draft dan hasil final tema dalam assignment Mentor aktif."
        eyebrow="M05 · Riwayat penilaian"
        status={
          <StatusBadge tone={participant?.follow_up_themes ? "warning" : "neutral"}>
            {participant?.follow_up_themes ?? 0} tindak lanjut
          </StatusBadge>
        }
        title={participant?.display_name ?? "Rekap peserta"}
      />
      {loading ? (
        <FeedbackState
          description="Mengambil ringkasan dan riwayat penilaian."
          title="Memuat rekap"
          tone="loading"
        />
      ) : null}
      {error ? (
        <FeedbackState
          action={
            <Button
              onClick={() => {
                setLoading(true);
                setReloadKey((value) => value + 1);
              }}
              variant="secondary"
            >
              Muat ulang
            </Button>
          }
          description={error}
          title="Rekap belum dapat dimuat"
          tone="error"
        />
      ) : null}
      {!loading && participant ? (
        <WorkSupportLayout
          support={
            <>
              <SupportPanel title="Ringkasan peserta">
                <dl className={styles.summary}>
                  <div>
                    <dt>NIM</dt>
                    <dd>{participant.nim}</dd>
                  </div>
                  <div>
                    <dt>Hasil final</dt>
                    <dd>{participant.final_assessments}</dd>
                  </div>
                  <div>
                    <dt>Tema Cukup</dt>
                    <dd>{participant.enough_themes}</dd>
                  </div>
                </dl>
              </SupportPanel>
              <SupportPanel title="Agregasi nilai Mentor">
                <p className={styles.supportCopy}>
                  Nilai Proses Hafalan (Mentor) belum dihitung sampai kebijakan agregasi disahkan. Riwayat ini tidak
                  menampilkan nilai buatan.
                </p>
              </SupportPanel>
            </>
          }
        >
          {history.length === 0 ? (
            <FeedbackState
              description="Belum ada draft atau hasil tema untuk peserta ini."
              title="Riwayat kosong"
            />
          ) : (
            <Card title={`Riwayat tema (${history.length})`}>
              <div className={styles.timeline}>
                {history.map((item) => (
                  <article key={item.assessment_id}>
                    <header>
                      <div>
                        <span>
                          {item.theme.code} · Kesempatan {item.attempt_no}
                        </span>
                        <h3>{item.theme.name}</h3>
                        <p>{dateTimeLabel(item.actual_at)}</p>
                      </div>
                      <div className={styles.badges}>
                        <StatusBadge tone={assessmentTone(item.status)}>
                          {assessmentStatusLabel[item.status]}
                        </StatusBadge>
                        <StatusBadge tone={outcomeTone(item.outcome)}>
                          {item.outcome ? outcomeLabel[item.outcome] : "Belum ditentukan"}
                        </StatusBadge>
                      </div>
                    </header>
                    <dl className={styles.facts}>
                      <div>
                        <dt>Skor</dt>
                        <dd>{item.manual_score ?? "Belum diisi"}</dd>
                      </div>
                      <div>
                        <dt>Kejadian dihitung</dt>
                        <dd>{item.counted_incidents}</dd>
                      </div>
                      <div>
                        <dt>Policy</dt>
                        <dd>{item.policy_version}</dd>
                      </div>
                    </dl>
                    {item.mentor_note ? <p className={styles.note}>{item.mentor_note}</p> : null}
                    {item.status === "draft" ? (
                      <Link className={styles.openLink} href={`/mentor/sesi/${item.session_id}`}>
                        Lanjutkan draft
                      </Link>
                    ) : null}
                  </article>
                ))}
              </div>
            </Card>
          )}
          {videoHistory.length && context ? (
            <section className={styles.timeline}>
              <h2>Riwayat video ({videoHistory.length})</h2>
              {videoHistory.map((item) => (
                <VideoAssessmentCard
                  assessment={item}
                  csrfToken={context.csrf_token}
                  key={item.assessment_id}
                  participant={false}
                />
              ))}
            </section>
          ) : null}
        </WorkSupportLayout>
      ) : null}
    </AppShell>
  );
}
