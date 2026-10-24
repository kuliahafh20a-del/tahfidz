"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { AppShell, PageHeader, SupportPanel, WorkSupportLayout } from "@/components/shell";
import { Button, Card, DataTable, FeedbackState, StatusBadge } from "@/components/ui";
import { apiRequest, CursorPage, SessionContext, Target } from "@/lib/mentoring";
import { VideoAttempt, VideoEligibility } from "@/lib/video";

import styles from "./workspace.module.css";

type PartChoice = {
  id: string;
  no: number;
  name: string;
  completed: number;
  total: number;
  eligible: boolean;
};

export function VideoSubmissionWorkspace() {
  const [context, setContext] = useState<SessionContext | null>(null);
  const [targets, setTargets] = useState<Target[]>([]);
  const [videoResults, setVideoResults] = useState<VideoEligibility[]>([]);
  const [partId, setPartId] = useState("");
  const [attempt, setAttempt] = useState<VideoAttempt | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void Promise.all([
      apiRequest<SessionContext>("/auth/session"),
      apiRequest<CursorPage<Target>>("/me/targets?limit=100"),
      apiRequest<VideoEligibility[]>("/me/video-results"),
    ])
      .then(([loadedContext, targetPage, loadedVideoResults]) => {
        if (!active) return;
        setContext(loadedContext);
        setTargets(targetPage.items);
        setVideoResults(loadedVideoResults);
        const replacement = loadedVideoResults.find((item) =>
          item.allowed_actions.includes("replace_video"),
        );
        if (replacement) setPartId(replacement.part_id);
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
  }, []);

  const parts = useMemo(() => {
    const grouped = new Map<string, PartChoice>();
    for (const target of targets) {
      const current = grouped.get(target.theme.part_id) ?? {
        id: target.theme.part_id,
        no: target.theme.part_no,
        name: target.theme.part_name,
        completed: 0,
        total: 0,
        eligible: false,
      };
      current.total += 1;
      if (target.status === "completed") current.completed += 1;
      current.eligible = current.completed === current.total;
      grouped.set(current.id, current);
    }
    return [...grouped.values()].sort((left, right) => right.no - left.no);
  }, [targets]);

  async function submitVideo(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!context || !partId) return;
    const form = event.currentTarget;
    const values = new FormData(form);
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      let activeAttempt = attempt;
      if (activeAttempt === null || activeAttempt.part_id !== partId) {
        const replacement = videoResults.find(
          (item) => item.part_id === partId && item.allowed_actions.includes("replace_video"),
        );
        activeAttempt = replacement
          ? await apiRequest<VideoAttempt>(`/video-attempts/${replacement.attempt_id}`)
          : await apiRequest<VideoAttempt>("/video-attempts", {
              method: "POST",
              headers: {
                "Idempotency-Key": crypto.randomUUID(),
                "X-CSRF-Token": context.csrf_token,
              },
              body: JSON.stringify({ part_id: partId }),
            });
        setAttempt(activeAttempt);
      }
      const updated = await apiRequest<VideoAttempt>(
        `/video-attempts/${activeAttempt.id}/versions`,
        {
          method: "POST",
          headers: {
            "Idempotency-Key": crypto.randomUUID(),
            "X-CSRF-Token": context.csrf_token,
          },
          body: JSON.stringify({
            video_url: values.get("video_url"),
            recorded_on: values.get("recorded_on"),
            completeness_declared: values.get("completeness_declared") === "on",
            expected_version: activeAttempt.row_version,
          }),
        },
      );
      setAttempt(updated);
      form.reset();
      setNotice(
        `Versi media ${updated.versions.at(-1)?.version_no ?? 1} tersimpan pada siklus ${updated.cycle_no}, revisi ${updated.revision_no}.`,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Video gagal dikirim.");
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
        breadcrumbs={[{ href: "/peserta", label: "Beranda" }, { label: "Kirim video" }]}
        description="Kirim tautan rekaman setelah seluruh tema dalam bagian memperoleh hasil Cukup."
        eyebrow="P04 · Setoran bagian"
        status={<StatusBadge tone="progress">Tautan HTTPS</StatusBadge>}
        title="Kirim video bagian"
      />

      {loading ? (
        <FeedbackState
          description="Memeriksa kelengkapan tema setiap bagian."
          title="Memuat"
          tone="loading"
        />
      ) : null}
      {error ? (
        <FeedbackState description={error} title="Kiriman belum dapat diproses" tone="error" />
      ) : null}
      {notice ? <FeedbackState description={notice} title="Video berhasil dikirim" /> : null}

      {!loading ? (
        <WorkSupportLayout
          support={
            <>
              <SupportPanel title="Syarat kiriman">
                <ul className={styles.rules}>
                  <li>Semua tema dalam bagian harus Cukup.</li>
                  <li>Tautan wajib HTTPS dari host yang diizinkan.</li>
                  <li>Pastikan rekaman lengkap sebelum mengirim.</li>
                </ul>
              </SupportPanel>
              <SupportPanel title="Penggantian teknis">
                <p className={styles.supportCopy}>
                  Tautan pengganti menambah versi media tanpa menaikkan revisi akademik.
                </p>
              </SupportPanel>
            </>
          }
        >
          <Card title="Kesiapan bagian">
            <DataTable
              caption="Status penyelesaian tema per bagian"
              headings={["Bagian", "Tema Cukup", "Status"]}
              rows={parts.map((part) => [
                `${part.no}. ${part.name}`,
                `${part.completed} dari ${part.total}`,
                <StatusBadge key={part.id} tone={part.eligible ? "success" : "neutral"}>
                  {part.eligible ? "Siap dikirim" : "Terkunci"}
                </StatusBadge>,
              ])}
            />
          </Card>

          <Card title="Tautan dan tanggal rekaman">
            {parts.some((part) => part.eligible) ? (
              <form className={styles.form} onSubmit={(event) => void submitVideo(event)}>
                <label>
                  Bagian
                  <select
                    disabled={busy || attempt !== null}
                    onChange={(event) => setPartId(event.target.value)}
                    required
                    value={partId}
                  >
                    <option value="">Pilih bagian</option>
                    {parts
                      .filter((part) => part.eligible)
                      .map((part) => (
                        <option key={part.id} value={part.id}>
                          Bagian {part.no} · {part.name}
                        </option>
                      ))}
                  </select>
                </label>
                <label>
                  Tanggal rekaman
                  <input
                    max={new Date().toISOString().slice(0, 10)}
                    name="recorded_on"
                    required
                    type="date"
                  />
                </label>
                <label className={styles.fullField}>
                  Tautan video
                  <input
                    name="video_url"
                    placeholder="https://www.youtube.com/watch?v=..."
                    required
                    type="url"
                  />
                </label>
                <label className={`${styles.fullField} ${styles.checkField}`}>
                  <input name="completeness_declared" required type="checkbox" />
                  <span>Saya memastikan rekaman lengkap dan dapat ditinjau.</span>
                </label>
                <Button disabled={busy || !partId} type="submit">
                  {attempt ? "Kirim video pengganti" : "Tinjau dan kirim video"}
                </Button>
              </form>
            ) : (
              <FeedbackState
                description="Selesaikan seluruh tema pada satu bagian terlebih dahulu."
                title="Setoran video masih terkunci"
                tone="locked"
              />
            )}
          </Card>

          {attempt ? (
            <Card title={`Siklus ${attempt.cycle_no} · Revisi ${attempt.revision_no}`}>
              <DataTable
                caption="Riwayat versi media pada slot akademik aktif"
                headings={["Versi", "Tanggal rekam", "Status", "Tautan"]}
                rows={attempt.versions.map((version) => [
                  version.version_no,
                  new Intl.DateTimeFormat("id-ID", { dateStyle: "medium" }).format(
                    new Date(`${version.recorded_on}T00:00:00`),
                  ),
                  version.status === "replaced" ? "Digantikan" : "Dikirim",
                  <a href={version.video_url} key={version.id} rel="noreferrer" target="_blank">
                    Buka video
                  </a>,
                ])}
              />
            </Card>
          ) : null}
        </WorkSupportLayout>
      ) : null}
    </AppShell>
  );
}
