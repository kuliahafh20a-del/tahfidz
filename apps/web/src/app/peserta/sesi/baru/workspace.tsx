"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { AppShell, PageHeader, SupportPanel, WorkSupportLayout } from "@/components/shell";
import { Button, Card, DataTable, FeedbackState, StatusBadge } from "@/components/ui";
import {
  apiRequest,
  CursorPage,
  dateTimeLabel,
  Session,
  SessionContext,
  sessionStatusLabel,
  sessionStatusTone,
  Target,
} from "@/lib/mentoring";

import styles from "./workspace.module.css";

export function SessionProposalWorkspace() {
  const [context, setContext] = useState<SessionContext | null>(null);
  const [targets, setTargets] = useState<Target[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    void Promise.all([
      apiRequest<SessionContext>("/auth/session"),
      apiRequest<CursorPage<Target>>("/me/targets?limit=100"),
      apiRequest<CursorPage<Session>>("/me/sessions?limit=100"),
    ])
      .then(([loadedContext, targetPage, sessionPage]) => {
        if (!active) return;
        setContext(loadedContext);
        setTargets(targetPage.items);
        setSessions(sessionPage.items);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof Error ? caught.message : "Data tidak tersedia.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reloadKey]);

  const actionableTargets = useMemo(
    () => targets.filter((target) => target.allowed_actions.includes("request_session")),
    [targets],
  );
  const selectedPart = actionableTargets.find((target) => selectedIds.has(target.theme.id))?.theme
    .part_id;

  function toggleTheme(target: Target): void {
    setSelectedIds((current) => {
      const next = target.theme.part_id === selectedPart ? new Set(current) : new Set<string>();
      if (next.has(target.theme.id)) next.delete(target.theme.id);
      else next.add(target.theme.id);
      return next;
    });
  }

  async function refreshSessions(): Promise<void> {
    const page = await apiRequest<CursorPage<Session>>("/me/sessions?limit=100");
    setSessions(page.items);
  }

  async function submitProposal(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!context || selectedIds.size === 0) return;
    const form = event.currentTarget;
    const values = new FormData(form);
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await apiRequest<Session>("/sessions", {
        method: "POST",
        headers: {
          "Idempotency-Key": crypto.randomUUID(),
          "X-CSRF-Token": context.csrf_token,
        },
        body: JSON.stringify({
          theme_ids: [...selectedIds],
          method: values.get("method"),
          proposed_at: new Date(String(values.get("proposed_at"))).toISOString(),
          participant_note: values.get("participant_note") || null,
        }),
      });
      form.reset();
      setSelectedIds(new Set());
      setNotice("Pengajuan sesi tersimpan dan menunggu jadwal Mentor.");
      await refreshSessions();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Pengajuan gagal disimpan.");
    } finally {
      setBusy(false);
    }
  }

  async function cancelSession(item: Session): Promise<void> {
    if (!context) return;
    setBusy(true);
    setError(null);
    try {
      await apiRequest<Session>(`/sessions/${item.id}/cancel`, {
        method: "POST",
        headers: {
          "Idempotency-Key": crypto.randomUUID(),
          "X-CSRF-Token": context.csrf_token,
        },
        body: JSON.stringify({ expected_version: item.row_version, note: "Dibatalkan peserta" }),
      });
      setNotice("Sesi dibatalkan dan tetap tersimpan dalam riwayat.");
      await refreshSessions();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Sesi gagal dibatalkan.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell
      accountName={context?.user.display_name ?? "Peserta"}
      initialRole="participant"
      organization={context?.active_context?.organization_name ?? "Program Tahfidz"}
    >
      <PageHeader
        breadcrumbs={[{ href: "/peserta", label: "Beranda" }, { label: "Ajukan sesi" }]}
        description="Pilih satu atau beberapa tema dalam bagian aktif yang sama, lalu usulkan waktu kepada Mentor."
        eyebrow="P03 · Pembimbingan"
        status={<StatusBadge tone="neutral">Waktu Jakarta</StatusBadge>}
        title="Ajukan sesi"
      />

      {loading ? (
        <FeedbackState
          description="Mengambil target aktif dan riwayat pengajuan Anda."
          title="Memuat sesi"
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
          title="Sesi belum dapat diproses"
          tone="error"
        />
      ) : null}
      {notice ? <FeedbackState description={notice} title="Berhasil" /> : null}

      {!loading ? (
        <WorkSupportLayout
          support={
            <>
              <SupportPanel title="Aturan pengajuan">
                <ul className={styles.rules}>
                  <li>Minimal satu tema.</li>
                  <li>Semua tema harus berasal dari satu bagian aktif.</li>
                  <li>Waktu usulan belum menjadi tanggal setoran pertama.</li>
                </ul>
              </SupportPanel>
              <SupportPanel title="Mentor aktif">
                <p className={styles.supportCopy}>
                  Sistem memilih Mentor dari assignment aktif. Mentor akan mengesahkan jadwal
                  sebelum sesi dapat dimulai.
                </p>
              </SupportPanel>
            </>
          }
        >
          <Card title="Tema bagian aktif">
            {actionableTargets.length === 0 ? (
              <FeedbackState
                description="Tidak ada tema aktif yang dapat diajukan saat ini. Tinjau target dan prasyarat bagian Anda."
                title="Pengajuan terkunci"
                tone="locked"
              />
            ) : (
              <div className={styles.themeGrid}>
                {actionableTargets.map((target) => (
                  <label className={styles.themeOption} key={target.theme.id}>
                    <input
                      checked={selectedIds.has(target.theme.id)}
                      disabled={busy}
                      onChange={() => toggleTheme(target)}
                      type="checkbox"
                    />
                    <span>
                      <strong>
                        {target.theme.code} · {target.theme.name}
                      </strong>
                      <small>{target.theme.part_name}</small>
                    </span>
                  </label>
                ))}
              </div>
            )}
          </Card>

          <Card title="Usulan waktu dan metode">
            <form className={styles.form} onSubmit={(event) => void submitProposal(event)}>
              <label>
                Usulan waktu
                <input name="proposed_at" required type="datetime-local" />
                <small>Zona waktu perangkat akan dikonversi ke waktu absolut.</small>
              </label>
              <label>
                Metode
                <select name="method" required>
                  <option value="video_call">Panggilan video</option>
                  <option value="in_person">Tatap muka</option>
                </select>
              </label>
              <label className={styles.fullField}>
                Catatan untuk Mentor
                <textarea name="participant_note" rows={3} />
              </label>
              <Button disabled={busy || selectedIds.size === 0} type="submit">
                Ajukan {selectedIds.size || ""} tema
              </Button>
            </form>
          </Card>

          <Card title="Riwayat sesi">
            {sessions.length === 0 ? (
              <FeedbackState
                description="Pengajuan pertama Anda akan muncul di sini."
                title="Belum ada sesi"
              />
            ) : (
              <DataTable
                caption="Riwayat pengajuan dan sesi peserta"
                headings={["Tema", "Status", "Usulan/jadwal", "Mentor", "Tindakan"]}
                rows={sessions.map((item) => [
                  item.themes.map((theme) => theme.code).join(", "),
                  <StatusBadge key={`${item.id}-status`} tone={sessionStatusTone(item.status)}>
                    {sessionStatusLabel[item.status]}
                  </StatusBadge>,
                  <span className={styles.timeStack} key={`${item.id}-time`}>
                    <span>Usulan: {dateTimeLabel(item.proposed_at)}</span>
                    <span>Jadwal: {dateTimeLabel(item.scheduled_at)}</span>
                  </span>,
                  item.mentor.display_name,
                  item.allowed_actions.includes("cancel") ? (
                    <Button
                      disabled={busy}
                      key={`${item.id}-cancel`}
                      onClick={() => void cancelSession(item)}
                      variant="danger"
                    >
                      Batalkan
                    </Button>
                  ) : (
                    "—"
                  ),
                ])}
              />
            )}
          </Card>
        </WorkSupportLayout>
      ) : null}
    </AppShell>
  );
}
