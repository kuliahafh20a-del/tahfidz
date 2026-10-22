"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { AppShell, PageHeader, SupportPanel, WorkSupportLayout } from "@/components/shell";
import { Button, Card, FeedbackState, StatusBadge } from "@/components/ui";
import {
  apiRequest,
  CursorPage,
  dateTimeLabel,
  Session,
  SessionContext,
  SessionStatus,
  sessionStatusLabel,
  sessionStatusTone,
  toLocalDateTime,
} from "@/lib/mentoring";

import styles from "./workspace.module.css";

const activeStatuses: SessionStatus[] = ["proposed", "scheduled", "in_progress"];

export function MentorQueueWorkspace() {
  const [context, setContext] = useState<SessionContext | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [filter, setFilter] = useState<SessionStatus | "all">("all");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    void Promise.all([
      apiRequest<SessionContext>("/auth/session"),
      apiRequest<CursorPage<Session>>("/mentor/queue?work_type=session&limit=100"),
    ])
      .then(([loadedContext, queue]) => {
        if (!active) return;
        setContext(loadedContext);
        setSessions(queue.items);
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

  const visibleSessions = useMemo(
    () => sessions.filter((item) => filter === "all" || item.status === filter),
    [filter, sessions],
  );
  const activeCount = sessions.filter((item) => activeStatuses.includes(item.status)).length;

  async function refreshQueue(): Promise<void> {
    const queue = await apiRequest<CursorPage<Session>>(
      "/mentor/queue?work_type=session&limit=100",
    );
    setSessions(queue.items);
  }

  async function scheduleSession(event: FormEvent<HTMLFormElement>, item: Session): Promise<void> {
    event.preventDefault();
    if (!context) return;
    const values = new FormData(event.currentTarget);
    setBusyId(item.id);
    setError(null);
    setNotice(null);
    try {
      await apiRequest<Session>(`/sessions/${item.id}`, {
        method: "PATCH",
        headers: {
          "Idempotency-Key": crypto.randomUUID(),
          "X-CSRF-Token": context.csrf_token,
        },
        body: JSON.stringify({
          scheduled_at: new Date(String(values.get("scheduled_at"))).toISOString(),
          method: values.get("method"),
          mentor_note: values.get("mentor_note") || null,
          expected_version: item.row_version,
        }),
      });
      setNotice("Jadwal disahkan. Tanggal ini belum dihitung sebagai tanggal setoran pertama.");
      await refreshQueue();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Jadwal gagal disimpan.");
      await refreshQueue().catch(() => undefined);
    } finally {
      setBusyId(null);
    }
  }

  async function transition(item: Session, action: "start" | "complete" | "no-show") {
    if (!context) return;
    setBusyId(item.id);
    setError(null);
    setNotice(null);
    try {
      await apiRequest<Session>(`/sessions/${item.id}/${action}`, {
        method: "POST",
        headers: {
          "Idempotency-Key": crypto.randomUUID(),
          "X-CSRF-Token": context.csrf_token,
        },
        body: JSON.stringify({
          expected_version: item.row_version,
          note:
            action === "start"
              ? "Sesi dimulai"
              : action === "complete"
                ? "Sesi selesai"
                : "Peserta tidak hadir",
        }),
      });
      setNotice(
        action === "start"
          ? "Sesi dimulai dan waktu aktual telah dicatat."
          : action === "complete"
            ? "Sesi ditutup sebagai selesai."
            : "Ketidakhadiran peserta telah dicatat.",
      );
      await refreshQueue();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Status sesi gagal diperbarui.");
      await refreshQueue().catch(() => undefined);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <AppShell
      accountName={context?.user.display_name ?? "Mentor"}
      initialRole="mentor"
      organization={context?.active_context?.organization_name ?? "Program Tahfidz"}
    >
      <PageHeader
        breadcrumbs={[{ href: "/", label: "Beranda" }, { label: "Binaan dan antrean" }]}
        description="Tinjau pengajuan peserta, sahkan jadwal, dan mulai sesi hanya dalam assignment aktif."
        eyebrow="M01 · Ruang kerja Mentor"
        status={<StatusBadge tone="progress">{activeCount} pekerjaan aktif</StatusBadge>}
        title="Binaan dan antrean"
      />

      {loading ? (
        <FeedbackState
          description="Mengambil pengajuan dan sesi dari peserta binaan aktif."
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
              variant="secondary"
            >
              Muat ulang
            </Button>
          }
          description={error}
          title="Antrean belum dapat diproses"
          tone="error"
        />
      ) : null}
      {notice ? <FeedbackState description={notice} title="Perubahan tersimpan" /> : null}

      {!loading ? (
        <WorkSupportLayout
          support={
            <>
              <SupportPanel title="Urutan sesi">
                <ol className={styles.steps}>
                  <li>Peserta mengajukan tema dan waktu.</li>
                  <li>Mentor mengesahkan jadwal.</li>
                  <li>Waktu aktual dicatat saat sesi dimulai.</li>
                  <li>Sesi selesai atau dicatat tidak hadir.</li>
                </ol>
              </SupportPanel>
              <SupportPanel title="Batas akses">
                <p className={styles.supportCopy}>
                  Antrean hanya memuat peserta dalam assignment Mentor yang masih aktif.
                </p>
              </SupportPanel>
            </>
          }
        >
          <Card title="Filter pekerjaan">
            <div className={styles.filters}>
              {(["all", ...activeStatuses, "completed", "no_show", "cancelled"] as const).map(
                (status) => (
                  <button
                    aria-pressed={filter === status}
                    key={status}
                    onClick={() => setFilter(status)}
                    type="button"
                  >
                    {status === "all" ? "Semua" : sessionStatusLabel[status]}
                  </button>
                ),
              )}
            </div>
          </Card>

          <Card title={`Antrean sesi (${visibleSessions.length})`}>
            {visibleSessions.length === 0 ? (
              <FeedbackState
                description="Tidak ada sesi yang sesuai dengan filter dan assignment aktif Anda."
                title="Antrean kosong"
              />
            ) : (
              <div className={styles.queue}>
                {visibleSessions.map((item) => (
                  <article className={styles.queueItem} key={item.id}>
                    <header>
                      <div>
                        <span className={styles.participantMeta}>{item.participant.nim}</span>
                        <h3>{item.participant.display_name}</h3>
                        <p>
                          {item.themes.map((theme) => `${theme.code} ${theme.name}`).join(" · ")}
                        </p>
                      </div>
                      <StatusBadge tone={sessionStatusTone(item.status)}>
                        {sessionStatusLabel[item.status]}
                      </StatusBadge>
                    </header>

                    <dl className={styles.sessionFacts}>
                      <div>
                        <dt>Usulan peserta</dt>
                        <dd>{dateTimeLabel(item.proposed_at)}</dd>
                      </div>
                      <div>
                        <dt>Jadwal disahkan</dt>
                        <dd>{dateTimeLabel(item.scheduled_at)}</dd>
                      </div>
                      <div>
                        <dt>Waktu aktual</dt>
                        <dd>{dateTimeLabel(item.actual_at)}</dd>
                      </div>
                    </dl>

                    {item.allowed_actions.some((action) =>
                      ["schedule", "reschedule"].includes(action),
                    ) ? (
                      <form
                        className={styles.scheduleForm}
                        onSubmit={(event) => void scheduleSession(event, item)}
                      >
                        <label>
                          Jadwal
                          <input
                            defaultValue={toLocalDateTime(item.scheduled_at ?? item.proposed_at)}
                            name="scheduled_at"
                            required
                            type="datetime-local"
                          />
                        </label>
                        <label>
                          Metode
                          <select defaultValue={item.method} name="method">
                            <option value="video_call">Panggilan video</option>
                            <option value="in_person">Tatap muka</option>
                          </select>
                        </label>
                        <label className={styles.noteField}>
                          Catatan Mentor
                          <input defaultValue={item.mentor_note ?? ""} name="mentor_note" />
                        </label>
                        <Button disabled={busyId === item.id} type="submit" variant="secondary">
                          {item.status === "proposed" ? "Sahkan jadwal" : "Perbarui jadwal"}
                        </Button>
                      </form>
                    ) : null}

                    <div className={styles.actions}>
                      {item.allowed_actions.includes("no_show") ? (
                        <Button
                          disabled={busyId === item.id}
                          onClick={() => void transition(item, "no-show")}
                          variant="danger"
                        >
                          Tidak hadir
                        </Button>
                      ) : null}
                      {item.allowed_actions.includes("start") ? (
                        <Button
                          disabled={busyId === item.id}
                          onClick={() => void transition(item, "start")}
                        >
                          Mulai sesi
                        </Button>
                      ) : null}
                      {item.allowed_actions.includes("complete") ? (
                        <Button
                          disabled={busyId === item.id}
                          onClick={() => void transition(item, "complete")}
                        >
                          Selesaikan sesi
                        </Button>
                      ) : null}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </Card>
        </WorkSupportLayout>
      ) : null}
    </AppShell>
  );
}
