"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { AppShell, PageHeader, SupportPanel, WorkSupportLayout } from "@/components/shell";
import { Button, Card, FeedbackState, StatusBadge } from "@/components/ui";
import {
  AssessmentIncident,
  assessmentStatusLabel,
  assessmentTone,
  emptyIncident,
  IncidentDraft,
  outcomeLabel,
  outcomeTone,
  ThemeAssessment,
  ThemeOutcome,
} from "@/lib/assessments";
import {
  apiRequest,
  dateTimeLabel,
  Session,
  SessionContext,
  toLocalDateTime,
} from "@/lib/mentoring";

import styles from "./workspace.module.css";

function incidentDraft(item: AssessmentIncident): IncidentDraft {
  return {
    location_text: item.location_text,
    primary_category: item.primary_category,
    context: item.context ?? "",
    assistance: item.assistance,
    self_corrected: item.self_corrected,
    counted: item.counted,
    counting_reason: item.counting_reason ?? "",
    note: item.note ?? "",
  };
}

export function ThemeAssessmentWorkspace({ sessionId }: { sessionId: string }) {
  const [context, setContext] = useState<SessionContext | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [assessments, setAssessments] = useState<ThemeAssessment[]>([]);
  const [selectedThemeId, setSelectedThemeId] = useState<string | null>(null);
  const [actualAt, setActualAt] = useState("");
  const [score, setScore] = useState("");
  const [outcome, setOutcome] = useState<ThemeOutcome | "">("");
  const [note, setNote] = useState("");
  const [incidents, setIncidents] = useState<IncidentDraft[]>([]);
  const [reviewing, setReviewing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    void Promise.all([
      apiRequest<SessionContext>("/auth/session"),
      apiRequest<Session>(`/mentor/sessions/${sessionId}`),
      apiRequest<ThemeAssessment[]>(`/sessions/${sessionId}/theme-assessments`),
    ])
      .then(([loadedContext, loadedSession, loadedAssessments]) => {
        if (!active) return;
        setContext(loadedContext);
        setSession(loadedSession);
        setAssessments(loadedAssessments);
        const initialThemeId = loadedSession.themes[0]?.theme_id ?? null;
        const initialAssessment = loadedAssessments.find(
          (item) => item.theme.theme_id === initialThemeId,
        );
        setSelectedThemeId(initialThemeId);
        setActualAt(
          toLocalDateTime(
            initialAssessment?.actual_at ?? loadedSession.actual_at ?? new Date().toISOString(),
          ),
        );
        setScore(initialAssessment?.manual_score?.toString() ?? "");
        setOutcome(initialAssessment?.outcome ?? "");
        setNote(initialAssessment?.mentor_note ?? "");
        setIncidents(initialAssessment?.incidents.map(incidentDraft) ?? []);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "Sesi tidak dapat dimuat.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reloadKey, sessionId]);

  const selectedTheme = session?.themes.find((item) => item.theme_id === selectedThemeId) ?? null;
  const selectedAssessment = useMemo(
    () => assessments.find((item) => item.theme.theme_id === selectedThemeId) ?? null,
    [assessments, selectedThemeId],
  );

  function chooseTheme(themeId: string) {
    if (!session) return;
    const assessment = assessments.find((item) => item.theme.theme_id === themeId);
    setSelectedThemeId(themeId);
    setActualAt(
      toLocalDateTime(assessment?.actual_at ?? session.actual_at ?? new Date().toISOString()),
    );
    setScore(assessment?.manual_score?.toString() ?? "");
    setOutcome(assessment?.outcome ?? "");
    setNote(assessment?.mentor_note ?? "");
    setIncidents(assessment?.incidents.map(incidentDraft) ?? []);
    setReviewing(false);
  }

  function updateIncident(index: number, changes: Partial<IncidentDraft>) {
    setIncidents((current) =>
      current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...changes } : item)),
    );
  }

  async function saveDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!context || !session || !selectedTheme) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    const payload = {
      actual_at: new Date(actualAt).toISOString(),
      manual_score: score ? Number(score) : null,
      outcome: outcome || null,
      mentor_note: note || null,
      incidents: incidents.map((item) => ({
        location_text: item.location_text,
        video_second: null,
        primary_category: item.primary_category,
        context: item.context || null,
        assistance: item.assistance,
        self_corrected: item.self_corrected,
        counted: item.counted,
        counting_reason: item.counting_reason || null,
        note: item.note || null,
      })),
    };
    try {
      const saved = selectedAssessment
        ? await apiRequest<ThemeAssessment>(
            `/theme-assessments/${selectedAssessment.assessment_id}`,
            {
              method: "PATCH",
              headers: {
                "Idempotency-Key": crypto.randomUUID(),
                "X-CSRF-Token": context.csrf_token,
              },
              body: JSON.stringify({
                ...payload,
                expected_version: selectedAssessment.row_version,
              }),
            },
          )
        : await apiRequest<ThemeAssessment>(`/sessions/${session.id}/theme-assessments`, {
            method: "POST",
            headers: {
              "Idempotency-Key": crypto.randomUUID(),
              "X-CSRF-Token": context.csrf_token,
            },
            body: JSON.stringify({ theme_id: selectedTheme.theme_id, ...payload }),
          });
      setAssessments((current) => [
        ...current.filter((item) => item.assessment_id !== saved.assessment_id),
        saved,
      ]);
      setNotice("Draft tersimpan. Tinjau seluruh bukti sebelum finalisasi.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Draft gagal disimpan.");
    } finally {
      setBusy(false);
    }
  }

  async function finalizeAssessment() {
    if (!context || !selectedAssessment) return;
    setBusy(true);
    setError(null);
    try {
      const finalized = await apiRequest<ThemeAssessment>(
        `/theme-assessments/${selectedAssessment.assessment_id}/finalize`,
        {
          method: "POST",
          headers: {
            "Idempotency-Key": crypto.randomUUID(),
            "X-CSRF-Token": context.csrf_token,
          },
          body: JSON.stringify({ expected_version: selectedAssessment.row_version }),
        },
      );
      setAssessments((current) =>
        current.map((item) => (item.assessment_id === finalized.assessment_id ? finalized : item)),
      );
      setReviewing(false);
      setNotice(
        finalized.outcome === "follow_up"
          ? "Hasil final tersimpan dan masuk tindak lanjut karena ini kesempatan kelima."
          : "Hasil tema telah difinalisasi dan tidak dapat diedit.",
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Finalisasi gagal diproses.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell
      accountName={context?.user.display_name ?? "Mentor"}
      initialRole="mentor"
      organization={context?.active_context?.organization_name ?? "Program Tahfidz"}
    >
      <PageHeader
        breadcrumbs={[
          { href: "/mentor/antrean", label: "Binaan dan antrean" },
          { label: "Catatan pembimbingan" },
        ]}
        description="Simpan draft per tema, periksa bukti, lalu finalisasi hasil secara aman."
        eyebrow="M02 · Penilaian tema"
        status={
          session ? (
            <StatusBadge tone={session.status === "in_progress" ? "progress" : "locked"}>
              {session.status === "in_progress" ? "Sesi berlangsung" : "Sesi terkunci"}
            </StatusBadge>
          ) : undefined
        }
        title="Catatan pembimbingan"
      />

      {loading ? (
        <FeedbackState
          description="Mengambil sesi, tema, dan draft tersimpan."
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
          title="Penilaian belum dapat diproses"
          tone="error"
        />
      ) : null}
      {notice ? <FeedbackState description={notice} title="Perubahan tersimpan" /> : null}

      {!loading && session ? (
        <WorkSupportLayout
          support={
            <>
              <SupportPanel title="Konteks sesi">
                <dl className={styles.summaryList}>
                  <div>
                    <dt>Peserta</dt>
                    <dd>{session.participant.display_name}</dd>
                  </div>
                  <div>
                    <dt>NIM</dt>
                    <dd>{session.participant.nim}</dd>
                  </div>
                  <div>
                    <dt>Waktu aktual</dt>
                    <dd>{dateTimeLabel(session.actual_at)}</dd>
                  </div>
                </dl>
              </SupportPanel>
              <SupportPanel title="Aturan finalisasi">
                <p className={styles.supportCopy}>
                  Skor final wajib bilangan bulat 1–10. Kesempatan kelima yang belum Cukup otomatis
                  menjadi tindak lanjut; kesempatan keenam tidak dibuat otomatis.
                </p>
              </SupportPanel>
            </>
          }
        >
          <Card title="Tema dalam sesi">
            <div className={styles.themeTabs}>
              {session.themes.map((theme) => {
                const item = assessments.find(
                  (assessment) => assessment.theme.theme_id === theme.theme_id,
                );
                return (
                  <button
                    aria-pressed={selectedThemeId === theme.theme_id}
                    key={theme.id}
                    onClick={() => chooseTheme(theme.theme_id)}
                    type="button"
                  >
                    <span>{theme.code}</span>
                    {theme.name}
                    <small>{item ? assessmentStatusLabel[item.status] : "Belum dinilai"}</small>
                  </button>
                );
              })}
            </div>
          </Card>

          {session.status !== "in_progress" && !selectedAssessment ? (
            <FeedbackState
              description="Mulai sesi dari antrean Mentor sebelum membuat penilaian tema."
              title="Form terkunci"
              tone="locked"
            />
          ) : null}

          {selectedTheme && (session.status === "in_progress" || selectedAssessment) ? (
            <Card title={`${selectedTheme.code} · ${selectedTheme.name}`}>
              {selectedAssessment ? (
                <div className={styles.assessmentMeta}>
                  <StatusBadge tone={assessmentTone(selectedAssessment.status)}>
                    {assessmentStatusLabel[selectedAssessment.status]}
                  </StatusBadge>
                  <span>Kesempatan {selectedAssessment.attempt_no} dari 5</span>
                  <span>Policy {selectedAssessment.policy_version}</span>
                </div>
              ) : null}

              <form className={styles.form} onSubmit={(event) => void saveDraft(event)}>
                <label>
                  Waktu aktual penilaian
                  <input
                    disabled={selectedAssessment?.status === "final"}
                    onChange={(event) => setActualAt(event.target.value)}
                    required
                    type="datetime-local"
                    value={actualAt}
                  />
                </label>
                <label>
                  Skor manual
                  <select
                    disabled={selectedAssessment?.status === "final"}
                    onChange={(event) => setScore(event.target.value)}
                    value={score}
                  >
                    <option value="">Belum diisi</option>
                    {Array.from({ length: 10 }, (_, index) => index + 1).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Hasil tema
                  <select
                    disabled={selectedAssessment?.status === "final"}
                    onChange={(event) => setOutcome(event.target.value as ThemeOutcome | "")}
                    value={outcome}
                  >
                    <option value="">Belum ditentukan</option>
                    <option value="enough">Cukup</option>
                    <option value="repeat">Ulangi</option>
                    {selectedAssessment?.attempt_no === 5 ? (
                      <option value="follow_up">Tindak lanjut</option>
                    ) : null}
                  </select>
                </label>
                <label className={styles.fullField}>
                  Catatan Mentor
                  <textarea
                    disabled={selectedAssessment?.status === "final"}
                    onChange={(event) => setNote(event.target.value)}
                    rows={3}
                    value={note}
                  />
                </label>

                <div className={styles.incidentHeader}>
                  <div>
                    <strong>Kejadian dan koreksi</strong>
                    <p>Catat satu kategori utama dan alasan apakah kejadian dihitung.</p>
                  </div>
                  {selectedAssessment?.status !== "final" ? (
                    <Button
                      onClick={() => setIncidents((current) => [...current, emptyIncident()])}
                      type="button"
                      variant="secondary"
                    >
                      Tambah kejadian
                    </Button>
                  ) : null}
                </div>

                {incidents.map((incident, index) => (
                  <fieldset className={styles.incident} key={index}>
                    <legend>Kejadian {index + 1}</legend>
                    <label>
                      Lokasi ayat
                      <input
                        disabled={selectedAssessment?.status === "final"}
                        onChange={(event) =>
                          updateIncident(index, { location_text: event.target.value })
                        }
                        required
                        value={incident.location_text}
                      />
                    </label>
                    <label>
                      Kategori utama
                      <select
                        disabled={selectedAssessment?.status === "final"}
                        onChange={(event) =>
                          updateIncident(index, { primary_category: event.target.value })
                        }
                        value={incident.primary_category}
                      >
                        <option value="tajwid">Tajwid</option>
                        <option value="word_choice">Pilihan kata</option>
                        <option value="sequence">Urutan ayat</option>
                        <option value="fluency">Kelancaran</option>
                      </select>
                    </label>
                    <label>
                      Bantuan
                      <select
                        disabled={selectedAssessment?.status === "final"}
                        onChange={(event) =>
                          updateIncident(index, {
                            assistance: event.target.value as IncidentDraft["assistance"],
                          })
                        }
                        value={incident.assistance}
                      >
                        <option value="none">Tanpa bantuan</option>
                        <option value="cue">Isyarat</option>
                        <option value="answer">Jawaban</option>
                      </select>
                    </label>
                    <label className={styles.fullField}>
                      Konteks
                      <input
                        disabled={selectedAssessment?.status === "final"}
                        onChange={(event) => updateIncident(index, { context: event.target.value })}
                        value={incident.context}
                      />
                    </label>
                    <label className={styles.checkField}>
                      <input
                        checked={incident.self_corrected}
                        disabled={selectedAssessment?.status === "final"}
                        onChange={(event) =>
                          updateIncident(index, { self_corrected: event.target.checked })
                        }
                        type="checkbox"
                      />
                      Dikoreksi mandiri
                    </label>
                    <label className={styles.checkField}>
                      <input
                        checked={incident.counted}
                        disabled={selectedAssessment?.status === "final"}
                        onChange={(event) =>
                          updateIncident(index, { counted: event.target.checked })
                        }
                        type="checkbox"
                      />
                      Dihitung sebagai kesalahan
                    </label>
                    <label className={styles.fullField}>
                      Alasan perhitungan
                      <input
                        disabled={selectedAssessment?.status === "final"}
                        onChange={(event) =>
                          updateIncident(index, { counting_reason: event.target.value })
                        }
                        required
                        value={incident.counting_reason}
                      />
                    </label>
                    {selectedAssessment?.status !== "final" ? (
                      <Button
                        onClick={() =>
                          setIncidents((current) =>
                            current.filter((_, itemIndex) => itemIndex !== index),
                          )
                        }
                        type="button"
                        variant="tertiary"
                      >
                        Hapus kejadian
                      </Button>
                    ) : null}
                  </fieldset>
                ))}

                {selectedAssessment?.status !== "final" ? (
                  <div className={styles.actions}>
                    <Button disabled={busy} type="submit" variant="secondary">
                      {busy ? "Menyimpan…" : "Simpan draft"}
                    </Button>
                    <Button
                      disabled={!selectedAssessment || busy}
                      onClick={() => setReviewing(true)}
                      type="button"
                    >
                      Tinjau hasil tema
                    </Button>
                  </div>
                ) : (
                  <div className={styles.finalSummary}>
                    <StatusBadge tone={outcomeTone(selectedAssessment?.outcome ?? null)}>
                      {selectedAssessment?.outcome
                        ? outcomeLabel[selectedAssessment.outcome]
                        : "Belum ada hasil"}
                    </StatusBadge>
                    <span>
                      Final pada {dateTimeLabel(selectedAssessment?.finalized_at ?? null)}
                    </span>
                  </div>
                )}
              </form>
            </Card>
          ) : null}

          {reviewing && selectedAssessment ? (
            <Card title="Tinjau sebelum finalisasi">
              <dl className={styles.reviewGrid}>
                <div>
                  <dt>Tema</dt>
                  <dd>{selectedAssessment.theme.name}</dd>
                </div>
                <div>
                  <dt>Kesempatan</dt>
                  <dd>{selectedAssessment.attempt_no} dari 5</dd>
                </div>
                <div>
                  <dt>Skor</dt>
                  <dd>{selectedAssessment.manual_score ?? "Belum diisi"}</dd>
                </div>
                <div>
                  <dt>Hasil</dt>
                  <dd>
                    {selectedAssessment.outcome
                      ? outcomeLabel[selectedAssessment.outcome]
                      : "Belum ditentukan"}
                  </dd>
                </div>
                <div>
                  <dt>Kejadian dihitung</dt>
                  <dd>{selectedAssessment.counted_incidents}</dd>
                </div>
                <div>
                  <dt>Policy</dt>
                  <dd>{selectedAssessment.policy_version}</dd>
                </div>
              </dl>
              <FeedbackState
                description="Finalisasi mengunci hasil. Koreksi berikutnya harus membuat record pengganti, bukan menimpa hasil ini."
                title="Konfirmasi hasil akademik"
                tone="locked"
              />
              <div className={styles.actions}>
                <Button onClick={() => setReviewing(false)} variant="secondary">
                  Kembali mengedit
                </Button>
                <Button disabled={busy} onClick={() => void finalizeAssessment()}>
                  {busy ? "Memfinalisasi…" : "Finalisasi hasil"}
                </Button>
              </div>
            </Card>
          ) : null}

          <div className={styles.footerLinks}>
            <Link href="/mentor/antrean">Kembali ke antrean</Link>
            <Link href={`/mentor/peserta/${session.participant.enrollment_id}`}>
              Buka rekap peserta
            </Link>
          </div>
        </WorkSupportLayout>
      ) : null}
    </AppShell>
  );
}
