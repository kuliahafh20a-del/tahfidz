"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AppShell, PageHeader, SupportPanel, WorkSupportLayout } from "@/components/shell";
import { Button, Card, FeedbackState, StatusBadge } from "@/components/ui";
import {
  assessmentStatusLabel,
  assessmentTone,
  outcomeLabel,
  outcomeTone,
  ThemeAssessment,
} from "@/lib/assessments";
import { apiRequest, CursorPage, dateTimeLabel, SessionContext } from "@/lib/mentoring";
import { VideoEligibility } from "@/lib/video";

import styles from "./workspace.module.css";

export function ParticipantResultsWorkspace() {
  const [context, setContext] = useState<SessionContext | null>(null);
  const [results, setResults] = useState<ThemeAssessment[]>([]);
  const [videoResults, setVideoResults] = useState<VideoEligibility[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    void Promise.all([
      apiRequest<SessionContext>("/auth/session"),
      apiRequest<CursorPage<ThemeAssessment>>("/me/theme-results?limit=100"),
      apiRequest<VideoEligibility[]>("/me/video-results"),
    ])
      .then(([loadedContext, page, loadedVideoResults]) => {
        if (!active) return;
        setContext(loadedContext);
        setResults(page.items);
        setVideoResults(loadedVideoResults);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof Error ? caught.message : "Hasil belum tersedia.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reloadKey]);

  const followUps = useMemo(
    () => results.filter((item) => item.outcome === "follow_up" || item.outcome === "repeat"),
    [results],
  );
  const enoughCount = results.filter((item) => item.outcome === "enough").length;
  const technicalFollowUps = videoResults.filter((item) =>
    item.allowed_actions.includes("replace_video"),
  );

  return (
    <AppShell
      accountName={context?.user.display_name ?? "Peserta"}
      initialRole="participant"
      organization={context?.active_context?.organization_name ?? "Program Tahfidz"}
    >
      <PageHeader
        breadcrumbs={[{ href: "/peserta", label: "Beranda" }, { label: "Hasil dan tindak lanjut" }]}
        description="Lihat hasil final setiap tema, bukti kejadian, dan langkah berikutnya."
        eyebrow="P05 · Riwayat akademik"
        status={
          <StatusBadge tone={followUps.length ? "warning" : "success"}>
            {followUps.length} tindak lanjut
          </StatusBadge>
        }
        title="Hasil dan tindak lanjut"
      />

      {loading ? (
        <FeedbackState
          description="Mengambil hasil final dari sesi pembimbingan."
          title="Memuat hasil"
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
              Coba lagi
            </Button>
          }
          description={error}
          title="Hasil belum dapat dimuat"
          tone="error"
        />
      ) : null}

      {!loading && !error ? (
        <WorkSupportLayout
          support={
            <>
              <SupportPanel title="Ringkasan tema">
                <dl className={styles.metrics}>
                  <div>
                    <dt>Hasil final</dt>
                    <dd>{results.length}</dd>
                  </div>
                  <div>
                    <dt>Cukup</dt>
                    <dd>{enoughCount}</dd>
                  </div>
                  <div>
                    <dt>Perlu tindakan</dt>
                    <dd>{followUps.length}</dd>
                  </div>
                  <div>
                    <dt>Video perlu diganti</dt>
                    <dd>{technicalFollowUps.length}</dd>
                  </div>
                </dl>
              </SupportPanel>
              <SupportPanel title="Langkah berikutnya">
                <p className={styles.supportCopy}>
                  Hasil Ulangi atau Tindak lanjut perlu dibahas pada sesi baru bersama Mentor.
                </p>
                <Link className={styles.actionLink} href="/peserta/sesi/baru">
                  Ajukan sesi revisi
                </Link>
              </SupportPanel>
            </>
          }
        >
          {results.length === 0 ? (
            <FeedbackState
              action={<Link href="/peserta/sesi/baru">Ajukan sesi pertama</Link>}
              description="Hasil akan muncul setelah Mentor memfinalisasi penilaian tema."
              title="Belum ada hasil final"
            />
          ) : (
            <div className={styles.results}>
              {results.map((item) => (
                <Card className={styles.resultCard} key={item.assessment_id}>
                  <header>
                    <div>
                      <span className={styles.themeCode}>{item.theme.code}</span>
                      <h2>{item.theme.name}</h2>
                      <p>
                        Kesempatan {item.attempt_no} · {dateTimeLabel(item.actual_at)}
                      </p>
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
                      <dd>{item.manual_score ?? "Belum dinilai"}</dd>
                    </div>
                    <div>
                      <dt>Kejadian dihitung</dt>
                      <dd>{item.counted_incidents}</dd>
                    </div>
                    <div>
                      <dt>Policy version</dt>
                      <dd>{item.policy_version}</dd>
                    </div>
                  </dl>
                  {item.mentor_note ? <p className={styles.note}>{item.mentor_note}</p> : null}
                  {item.incidents.length ? (
                    <details>
                      <summary>Lihat {item.incidents.length} catatan kejadian</summary>
                      <ul className={styles.incidents}>
                        {item.incidents.map((incident) => (
                          <li key={incident.id}>
                            <strong>{incident.location_text}</strong> · {incident.primary_category}
                            <span>{incident.counting_reason}</span>
                          </li>
                        ))}
                      </ul>
                    </details>
                  ) : null}
                  {item.outcome !== "enough" ? (
                    <Link className={styles.actionLink} href="/peserta/sesi/baru">
                      Ajukan sesi revisi
                    </Link>
                  ) : null}
                </Card>
              ))}
            </div>
          )}

          {videoResults.length ? (
            <Card title="Kelayakan teknis video">
              <div className={styles.results}>
                {videoResults.map((item) => (
                  <article className={styles.videoResult} key={item.video_version_id}>
                    <header>
                      <div>
                        <h2>
                          Bagian {item.part_no} · {item.part_name}
                        </h2>
                        <p>
                          Siklus {item.cycle_no} · Revisi {item.revision_no} · Versi media{" "}
                          {item.video_version_no}
                        </p>
                      </div>
                      <StatusBadge
                        tone={
                          item.review?.decision === "eligible"
                            ? "success"
                            : item.review?.decision === "ineligible"
                              ? "danger"
                              : "warning"
                        }
                      >
                        {item.review?.decision === "eligible"
                          ? "Layak"
                          : item.review?.decision === "ineligible"
                            ? "Tidak layak"
                            : item.review
                              ? "Draft Mentor"
                              : "Menunggu pemeriksaan"}
                      </StatusBadge>
                    </header>
                    {item.review?.decision === "ineligible" ? (
                      <div className={styles.technicalReason}>
                        <strong>Alasan teknis</strong>
                        <p>{item.review.reason}</p>
                      </div>
                    ) : null}
                    {item.allowed_actions.includes("replace_video") ? (
                      <Link className={styles.actionLink} href="/peserta/video/baru">
                        Kirim video pengganti
                      </Link>
                    ) : null}
                  </article>
                ))}
              </div>
            </Card>
          ) : null}
        </WorkSupportLayout>
      ) : null}
    </AppShell>
  );
}
