"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { AppShell, PageHeader, SupportPanel, WorkSupportLayout } from "@/components/shell";
import { Button, Card, FeedbackState, StatusBadge } from "@/components/ui";
import { apiRequest, SessionContext } from "@/lib/mentoring";
import {
  VideoAssessment,
  VideoAssessmentIncident,
  VideoEligibility,
  videoOutcomeLabel,
} from "@/lib/video";

import styles from "./workspace.module.css";

type DraftIncident = Omit<VideoAssessmentIncident, "id">;

const emptyIncident = (): DraftIncident => ({
  location_text: "",
  video_second: 0,
  primary_category: "word_choice",
  context: null,
  assistance: "none",
  self_corrected: false,
  counted: true,
  counting_reason: "",
  note: null,
});

const editableIncident = (value: VideoAssessmentIncident): DraftIncident => ({
  location_text: value.location_text,
  video_second: value.video_second,
  primary_category: value.primary_category,
  context: value.context,
  assistance: value.assistance,
  self_corrected: value.self_corrected,
  counted: value.counted,
  counting_reason: value.counting_reason,
  note: value.note,
});

export function VideoAssessmentWorkspace() {
  const [context, setContext] = useState<SessionContext | null>(null);
  const [eligible, setEligible] = useState<VideoEligibility[]>([]);
  const [assessments, setAssessments] = useState<VideoAssessment[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    void Promise.all([
      apiRequest<SessionContext>("/auth/session"),
      apiRequest<VideoEligibility[]>("/mentor/video-versions"),
      apiRequest<VideoAssessment[]>("/mentor/video-assessments"),
    ])
      .then(([loadedContext, versions, loadedAssessments]) => {
        if (!active) return;
        const candidates = versions.filter((item) => item.review?.decision === "eligible");
        setContext(loadedContext);
        setEligible(candidates);
        setAssessments(loadedAssessments);
        setSelectedId((current) => current ?? candidates[0]?.video_version_id ?? null);
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

  const selected = useMemo(
    () => eligible.find((item) => item.video_version_id === selectedId) ?? null,
    [eligible, selectedId],
  );
  const selectedAssessment =
    assessments.find((item) => item.video_version_id === selectedId) ?? null;
  const drafts = assessments.filter((item) => item.status === "draft").length;

  function updateAssessment(value: VideoAssessment, message: string) {
    setAssessments((current) => [
      value,
      ...current.filter((item) => item.assessment_id !== value.assessment_id),
    ]);
    setNotice(message);
    setError(null);
  }

  return (
    <AppShell
      accountName={context?.user.display_name ?? "Mentor"}
      initialRole="mentor"
      organization={context?.active_context?.organization_name ?? "Program Tahfidz"}
    >
      <PageHeader
        breadcrumbs={[
          { href: "/mentor/video/kelayakan", label: "Kelayakan" },
          { label: "Penilaian video" },
        ]}
        description="Nilai rekaman yang telah Layak; hasil dihitung dari kejadian terhitung, bukan skor manual."
        eyebrow="M04 · Penilaian akademik"
        status={<StatusBadge tone={drafts ? "warning" : "neutral"}>{drafts} draft</StatusBadge>}
        title="Penilaian video"
      />
      {loading ? (
        <FeedbackState description="Mengambil video Layak." title="Memuat antrean" tone="loading" />
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
          title="Penilaian belum dapat diproses"
          tone="error"
        />
      ) : null}
      {notice ? <FeedbackState description={notice} title="Perubahan tersimpan" /> : null}

      {!loading && !error ? (
        <WorkSupportLayout
          support={
            <>
              <SupportPanel title="Aturan hasil">
                <p className={styles.supportCopy}>
                  0–3 kesalahan terhitung adalah Cukup; 4 atau lebih adalah Belum Cukup. Ambang
                  dibaca dari policy version.
                </p>
              </SupportPanel>
              <SupportPanel title="Sebelum finalisasi">
                <p className={styles.supportCopy}>
                  Skor memakai bilangan bulat 1–10. Audio Mentor harus selesai divalidasi dan setiap
                  kejadian harus memiliki alasan hitung.
                </p>
              </SupportPanel>
            </>
          }
        >
          <Card title={`Video Layak (${eligible.length})`}>
            {eligible.length === 0 ? (
              <FeedbackState
                description="Finalisasi kelayakan video terlebih dahulu di M03."
                title="Belum ada video Layak"
              />
            ) : (
              <div className={styles.queue}>
                {eligible.map((item) => {
                  const assessment = assessments.find(
                    (value) => value.video_version_id === item.video_version_id,
                  );
                  return (
                    <button
                      aria-pressed={selectedId === item.video_version_id}
                      className={styles.queueItem}
                      key={item.video_version_id}
                      onClick={() => {
                        setSelectedId(item.video_version_id);
                        setNotice(null);
                      }}
                      type="button"
                    >
                      <span>
                        <strong>{item.participant.display_name}</strong>
                        <small>
                          {item.participant.nim} · Bagian {item.part_no} · Revisi {item.revision_no}
                        </small>
                      </span>
                      <StatusBadge tone={assessment?.status === "final" ? "success" : "warning"}>
                        {assessment?.status === "final"
                          ? videoOutcomeLabel[assessment.outcome ?? "not_enough"]
                          : assessment
                            ? "Draft"
                            : "Belum dinilai"}
                      </StatusBadge>
                    </button>
                  );
                })}
              </div>
            )}
          </Card>
          {selected && context ? (
            <AssessmentEditor
              assessment={selectedAssessment}
              item={selected}
              key={`${selected.video_version_id}-${selectedAssessment?.row_version ?? 0}`}
              onError={setError}
              onUpdated={updateAssessment}
              session={context}
            />
          ) : null}
        </WorkSupportLayout>
      ) : null}
    </AppShell>
  );
}

function AssessmentEditor({
  assessment,
  item,
  onError,
  onUpdated,
  session,
}: {
  assessment: VideoAssessment | null;
  item: VideoEligibility;
  onError: (message: string | null) => void;
  onUpdated: (assessment: VideoAssessment, message: string) => void;
  session: SessionContext;
}) {
  const [busy, setBusy] = useState(false);
  const [audioId, setAudioId] = useState(assessment?.feedback_audio?.id ?? null);
  const [audioStatus, setAudioStatus] = useState(assessment?.feedback_audio?.status ?? null);
  const [incidents, setIncidents] = useState<DraftIncident[]>(
    assessment?.incidents.map(editableIncident) ?? [],
  );
  const isFinal = assessment?.status === "final";
  const counted = incidents.filter((incident) => incident.counted).length;

  async function uploadAudio(file: File): Promise<void> {
    setBusy(true);
    onError(null);
    try {
      const hash = Array.from(
        new Uint8Array(await crypto.subtle.digest("SHA-256", await file.arrayBuffer())),
      )
        .map((value) => value.toString(16).padStart(2, "0"))
        .join("");
      const intent = await apiRequest<{
        media: { id: string; status: string };
        upload_url: string;
        required_headers: Record<string, string>;
      }>("/media/audio/upload-intents", {
        method: "POST",
        headers: { "X-CSRF-Token": session.csrf_token },
        body: JSON.stringify({
          file_name: file.name,
          content_type: file.type,
          size_bytes: file.size,
          sha256: hash,
          purpose: "mentor_feedback",
        }),
      });
      const uploaded = await fetch(intent.upload_url, {
        method: "PUT",
        headers: intent.required_headers,
        body: file,
      });
      if (!uploaded.ok) throw new Error("Unggah audio ke penyimpanan gagal.");
      const completed = await apiRequest<{ id: string; status: typeof audioStatus }>(
        `/media/${intent.media.id}/complete`,
        {
          method: "POST",
          headers: { "X-CSRF-Token": session.csrf_token },
        },
      );
      setAudioId(completed.id);
      setAudioStatus(completed.status);
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Audio gagal diunggah.");
    } finally {
      setBusy(false);
    }
  }

  function patchIncident(index: number, patch: Partial<DraftIncident>) {
    setIncidents((current) =>
      current.map((value, position) => (position === index ? { ...value, ...patch } : value)),
    );
  }

  async function save(form: HTMLFormElement, finalize: boolean) {
    setBusy(true);
    onError(null);
    try {
      const values = new FormData(form);
      const payload = {
        manual_score: Number(values.get("manual_score")) || null,
        mentor_note: values.get("mentor_note") || null,
        feedback_audio_id: audioId,
        incidents,
      };
      const updated = await apiRequest<VideoAssessment>(
        assessment
          ? `/video-assessments/${assessment.assessment_id}`
          : `/video-versions/${item.video_version_id}/assessment`,
        {
          method: assessment ? "PATCH" : "POST",
          headers: { "Idempotency-Key": crypto.randomUUID(), "X-CSRF-Token": session.csrf_token },
          body: JSON.stringify(
            assessment ? { ...payload, expected_version: assessment.row_version } : payload,
          ),
        },
      );
      if (!finalize) {
        onUpdated(updated, "Draft penilaian video tersimpan.");
        return;
      }
      const finalized = await apiRequest<VideoAssessment>(
        `/video-assessments/${updated.assessment_id}/finalize`,
        {
          method: "POST",
          headers: { "Idempotency-Key": crypto.randomUUID(), "X-CSRF-Token": session.csrf_token },
          body: JSON.stringify({ expected_version: updated.row_version }),
        },
      );
      onUpdated(
        finalized,
        `Penilaian difinalisasi dengan hasil ${videoOutcomeLabel[finalized.outcome ?? "not_enough"]}.`,
      );
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Penilaian gagal disimpan.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title={`${item.participant.display_name} · ${item.part_name}`}>
      <div className={styles.videoMeta}>
        <span>
          Siklus {item.cycle_no} · Revisi {item.revision_no} · Versi media {item.video_version_no}
        </span>
        <a href={item.video_url} rel="noreferrer" target="_blank">
          Buka rekaman video
        </a>
      </div>
      <form
        className={styles.form}
        onSubmit={(event: FormEvent<HTMLFormElement>) => {
          event.preventDefault();
          void save(event.currentTarget, false);
        }}
      >
        <label>
          Skor manual
          <input
            defaultValue={assessment?.manual_score ?? ""}
            disabled={isFinal}
            max={10}
            min={1}
            name="manual_score"
            required
            type="number"
          />
        </label>
        <label>
          Audio umpan balik
          <input
            accept="audio/*"
            disabled={busy || isFinal}
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file) void uploadAudio(file);
            }}
            type="file"
          />
        </label>
        <p className={styles.audioState}>
          Status audio: {audioStatus ?? "belum dipilih"}
          {audioStatus && audioStatus !== "available"
            ? " — tunggu worker validasi lalu muat ulang sebelum finalisasi"
            : ""}
        </p>
        <section className={styles.incidentSection}>
          <header>
            <div>
              <h3>Kejadian</h3>
              <p>
                {counted} kesalahan terhitung · prediksi {counted <= 3 ? "Cukup" : "Belum Cukup"}
              </p>
            </div>
            {!isFinal ? (
              <Button
                onClick={() => setIncidents((current) => [...current, emptyIncident()])}
                type="button"
                variant="secondary"
              >
                Tambah kejadian
              </Button>
            ) : null}
          </header>
          {incidents.map((incident, index) => (
            <fieldset className={styles.incident} disabled={isFinal} key={index}>
              <label>
                Ayat/lokasi
                <input
                  onChange={(event) => patchIncident(index, { location_text: event.target.value })}
                  required
                  value={incident.location_text}
                />
              </label>
              <label>
                Detik video
                <input
                  min={0}
                  onChange={(event) =>
                    patchIncident(index, { video_second: Number(event.target.value) })
                  }
                  required
                  type="number"
                  value={incident.video_second ?? 0}
                />
              </label>
              <label>
                Kategori
                <input
                  onChange={(event) =>
                    patchIncident(index, { primary_category: event.target.value })
                  }
                  required
                  value={incident.primary_category}
                />
              </label>
              <label>
                Alasan hitung
                <input
                  onChange={(event) =>
                    patchIncident(index, { counting_reason: event.target.value })
                  }
                  required
                  value={incident.counting_reason ?? ""}
                />
              </label>
              <label className={styles.check}>
                <input
                  checked={incident.self_corrected}
                  onChange={(event) =>
                    patchIncident(index, { self_corrected: event.target.checked })
                  }
                  type="checkbox"
                />
                Dikoreksi mandiri
              </label>
              <label className={styles.check}>
                <input
                  checked={incident.counted}
                  onChange={(event) => patchIncident(index, { counted: event.target.checked })}
                  type="checkbox"
                />
                Dihitung sebagai kesalahan
              </label>
              {!isFinal ? (
                <Button
                  onClick={() =>
                    setIncidents((current) =>
                      current.filter((_value, position) => position !== index),
                    )
                  }
                  type="button"
                  variant="secondary"
                >
                  Hapus
                </Button>
              ) : null}
            </fieldset>
          ))}
        </section>
        <label>
          Catatan Mentor
          <textarea
            defaultValue={assessment?.mentor_note ?? ""}
            disabled={isFinal}
            name="mentor_note"
            rows={4}
          />
        </label>
        {isFinal ? (
          <FeedbackState
            description={`Hasil ${videoOutcomeLabel[assessment.outcome ?? "not_enough"]} bersifat final.`}
            title="Penilaian telah final"
          />
        ) : (
          <div className={styles.actions}>
            <Button disabled={busy} type="submit" variant="secondary">
              Simpan draft
            </Button>
            <Button
              disabled={busy || audioStatus !== "available"}
              onClick={(event) => {
                const form = event.currentTarget.form;
                if (form) void save(form, true);
              }}
              type="button"
            >
              Tinjau dan finalisasi
            </Button>
          </div>
        )}
      </form>
    </Card>
  );
}
