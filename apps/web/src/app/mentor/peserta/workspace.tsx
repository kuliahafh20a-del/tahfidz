"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell, PageHeader } from "@/components/shell";
import { Button, Card, FeedbackState, StatusBadge } from "@/components/ui";
import { MentorParticipant } from "@/lib/assessments";
import { apiRequest, CursorPage, SessionContext } from "@/lib/mentoring";

import styles from "./workspace.module.css";

export function MentorParticipantsWorkspace() {
  const [context, setContext] = useState<SessionContext | null>(null);
  const [participants, setParticipants] = useState<MentorParticipant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    void Promise.all([
      apiRequest<SessionContext>("/auth/session"),
      apiRequest<CursorPage<MentorParticipant>>("/mentor/participants?limit=100"),
    ])
      .then(([loadedContext, page]) => {
        if (!active) return;
        setContext(loadedContext);
        setParticipants(page.items);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof Error ? caught.message : "Peserta tidak tersedia.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reloadKey]);

  return (
    <AppShell
      accountName={context?.user.display_name ?? "Mentor"}
      initialRole="mentor"
      organization={context?.active_context?.organization_name ?? "Program Tahfidz"}
    >
      <PageHeader
        breadcrumbs={[
          { href: "/mentor/antrean", label: "Binaan dan antrean" },
          { label: "Rekap peserta" },
        ]}
        description="Pilih peserta dalam assignment aktif untuk melihat riwayat tema dan tindak lanjut."
        eyebrow="M05 · Rekap peserta"
        status={<StatusBadge tone="neutral">{participants.length} peserta binaan</StatusBadge>}
        title="Rekap peserta"
      />
      {loading ? (
        <FeedbackState
          description="Mengambil peserta dalam assignment aktif."
          title="Memuat peserta"
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
          title="Daftar peserta belum dapat dimuat"
          tone="error"
        />
      ) : null}
      {!loading && !error && participants.length === 0 ? (
        <FeedbackState
          description="Tidak ada peserta dengan assignment Mentor yang aktif."
          title="Belum ada peserta binaan"
        />
      ) : null}
      {!loading && !error && participants.length ? (
        <div className={styles.grid}>
          {participants.map((participant) => (
            <Card key={participant.enrollment_id}>
              <span className={styles.nim}>{participant.nim}</span>
              <h2>{participant.display_name}</h2>
              <dl className={styles.metrics}>
                <div>
                  <dt>Hasil final</dt>
                  <dd>{participant.final_assessments}</dd>
                </div>
                <div>
                  <dt>Cukup</dt>
                  <dd>{participant.enough_themes}</dd>
                </div>
                <div>
                  <dt>Tindak lanjut</dt>
                  <dd>{participant.follow_up_themes}</dd>
                </div>
              </dl>
              <Link
                className={styles.detailLink}
                href={`/mentor/peserta/${participant.enrollment_id}`}
              >
                Buka riwayat penilaian
              </Link>
            </Card>
          ))}
        </div>
      ) : null}
    </AppShell>
  );
}
