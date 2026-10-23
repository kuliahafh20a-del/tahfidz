"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell, PageHeader, SupportPanel, WorkSupportLayout } from "@/components/shell";
import { Button, Card, FeedbackState, StatusBadge } from "@/components/ui";
import { Exam, ExamQueueItem, examStatusLabel } from "@/lib/exams";
import { apiRequest, SessionContext } from "@/lib/mentoring";

import styles from "./workspace.module.css";

function tomorrowAtNine(): string {
  const value = new Date();
  value.setDate(value.getDate() + 1);
  value.setHours(9, 0, 0, 0);
  return new Date(value.getTime() - value.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

export function ExamQueueWorkspace() {
  const [context, setContext] = useState<SessionContext | null>(null);
  const [queue, setQueue] = useState<ExamQueueItem[]>([]);
  const [schedule, setSchedule] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    void Promise.all([
      apiRequest<SessionContext>("/auth/session"),
      apiRequest<ExamQueueItem[]>("/lecturer/exam-queue"),
    ])
      .then(([loadedContext, loadedQueue]) => {
        if (!active) return;
        setContext(loadedContext);
        setQueue(loadedQueue);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof Error ? caught.message : "Antrean tidak tersedia.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reloadKey]);

  async function createExam(item: ExamQueueItem) {
    if (!context) return;
    setBusyId(item.participant.enrollment_id);
    setError(null);
    try {
      const exam = await apiRequest<Exam>("/exams", {
        method: "POST",
        headers: {
          "Idempotency-Key": crypto.randomUUID(),
          "X-CSRF-Token": context.csrf_token,
        },
        body: JSON.stringify({
          enrollment_id: item.participant.enrollment_id,
          scheduled_at: new Date(
            schedule[item.participant.enrollment_id] ?? tomorrowAtNine(),
          ).toISOString(),
        }),
      });
      setQueue((current) =>
        current.map((value) =>
          value.participant.enrollment_id === item.participant.enrollment_id
            ? {
                ...value,
                latest_exam_id: exam.id,
                latest_exam_status: exam.status,
                allowed_actions: ["open_exam"],
              }
            : value,
        ),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Draft ujian gagal dibuat.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <AppShell
      accountName={context?.user.display_name ?? "Dosen"}
      initialRole="lecturer"
      organization={context?.active_context?.organization_name ?? "Program Tahfidz"}
    >
      <PageHeader
        breadcrumbs={[{ label: "Antrean ujian" }]}
        description="Peserta muncul setelah lima bagian hafalan memperoleh hasil video Cukup."
        eyebrow="D01 · Kesiapan ujian"
        status={<StatusBadge tone="progress">{queue.length} siap ujian</StatusBadge>}
        title="Antrean ujian"
      />
      {loading ? (
        <FeedbackState
          description="Memeriksa hasil lima bagian dan assignment Dosen."
          title="Memuat antrean"
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
            >
              Muat ulang
            </Button>
          }
          description={error}
          title="Antrean belum dapat dimuat"
          tone="error"
        />
      ) : null}
      {!loading && !error ? (
        <WorkSupportLayout
          support={
            <>
              <SupportPanel title="Syarat antrean">
                <p className={styles.supportCopy}>
                  Kelima bagian harus memiliki penilaian video final Cukup dan peserta berada dalam
                  assignment Dosen yang masih aktif.
                </p>
              </SupportPanel>
              <SupportPanel title="Kebijakan paket">
                <p className={styles.supportCopy}>
                  Draft paket dapat disiapkan sekarang. Pelaksanaan tetap terkunci sampai jumlah dan
                  bobot soal disahkan.
                </p>
              </SupportPanel>
            </>
          }
        >
          {queue.length === 0 ? (
            <FeedbackState
              description="Belum ada peserta binaan Dosen yang menyelesaikan lima bagian."
              title="Antrean kosong"
            />
          ) : (
            <div className={styles.queue}>
              {queue.map((item) => (
                <Card className={styles.queueCard} key={item.participant.enrollment_id}>
                  <header>
                    <div>
                      <h2>{item.participant.display_name}</h2>
                      <p>
                        {item.participant.nim} · {item.completed_parts}/{item.required_parts} bagian
                        Cukup
                      </p>
                    </div>
                    <StatusBadge tone="success">Siap ujian</StatusBadge>
                  </header>
                  {item.latest_exam_id ? (
                    <div className={styles.actions}>
                      <span>
                        {item.latest_exam_status
                          ? examStatusLabel[item.latest_exam_status]
                          : "Draft tersedia"}
                      </span>
                      <Link href={`/dosen/ujian/${item.latest_exam_id}/paket`}>
                        Buka paket ujian
                      </Link>
                    </div>
                  ) : (
                    <div className={styles.actions}>
                      <label>
                        Jadwal awal
                        <input
                          min={tomorrowAtNine()}
                          onChange={(event) =>
                            setSchedule((current) => ({
                              ...current,
                              [item.participant.enrollment_id]: event.target.value,
                            }))
                          }
                          type="datetime-local"
                          value={schedule[item.participant.enrollment_id] ?? tomorrowAtNine()}
                        />
                      </label>
                      <Button
                        disabled={busyId === item.participant.enrollment_id}
                        onClick={() => void createExam(item)}
                      >
                        Buat draft paket
                      </Button>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </WorkSupportLayout>
      ) : null}
    </AppShell>
  );
}
