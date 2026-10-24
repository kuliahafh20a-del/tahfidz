"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AppShell, PageHeader, SupportPanel, WorkSupportLayout } from "@/components/shell";
import { Button, Card, FeedbackState, StatusBadge } from "@/components/ui";
import { Exam, questionKindLabel } from "@/lib/exams";
import { apiRequest, dateTimeLabel, SessionContext } from "@/lib/mentoring";

import styles from "../exam-workspace.module.css";

type ItemDraft = { score: string; notes: string; evidence: string };

const blockerLabel: Record<string, string> = {
  exam_package_policy_not_approved: "DEC-002 belum mengesahkan jumlah, bobot, dan agregasi soal.",
  exam_item_count_mismatch: "Jumlah soal belum sesuai kebijakan.",
  exam_item_weights_incomplete: "Bobot soal belum lengkap.",
  exam_item_weight_total_mismatch: "Total bobot belum sesuai kebijakan.",
  exam_item_assessments_incomplete: "Semua butir harus memiliki skor.",
};

function draftsFromExam(exam: Exam): Record<string, ItemDraft> {
  return Object.fromEntries(
    exam.items.map((item) => {
      const assessment = exam.assessments.find((entry) => entry.exam_item_id === item.id);
      return [
        item.id,
        {
          score: assessment?.manual_score?.toString() ?? "",
          notes: assessment?.notes ?? "",
          evidence: assessment?.incidents[0]?.location_text ?? "",
        },
      ];
    }),
  );
}

export function ExamExecutionWorkspace({ examId }: { examId: string }) {
  const [context, setContext] = useState<SessionContext | null>(null);
  const [exam, setExam] = useState<Exam | null>(null);
  const [drafts, setDrafts] = useState<Record<string, ItemDraft>>({});
  const [evidenceIds, setEvidenceIds] = useState("");
  const [examinerNote, setExaminerNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([
      apiRequest<SessionContext>("/auth/session"),
      apiRequest<Exam>(`/exams/${examId}`),
    ])
      .then(([session, loadedExam]) => {
        setContext(session);
        setExam(loadedExam);
        setDrafts(draftsFromExam(loadedExam));
        setEvidenceIds(loadedExam.evidence_media_ids.join(", "));
        setExaminerNote(loadedExam.lecturer_note ?? "");
      })
      .catch((caught: unknown) =>
        setError(caught instanceof Error ? caught.message : "Ujian tidak tersedia."),
      )
      .finally(() => setLoading(false));
  }, [examId]);

  const complete = useMemo(
    () => exam?.items.every((item) => /^([1-9]|10)$/.test(drafts[item.id]?.score ?? "")) ?? false,
    [drafts, exam],
  );

  function updateDraft(itemId: string, field: keyof ItemDraft, value: string) {
    setDrafts((current) => ({
      ...current,
      [itemId]: {
        ...(current[itemId] ?? { score: "", notes: "", evidence: "" }),
        [field]: value,
      },
    }));
  }

  async function mutate(path: string, method: "POST" | "PUT", body: object, message: string) {
    if (!context) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await apiRequest<Exam>(path, {
        method,
        headers: { "Idempotency-Key": crypto.randomUUID(), "X-CSRF-Token": context.csrf_token },
        body: JSON.stringify(body),
      });
      setExam(updated);
      setDrafts(draftsFromExam(updated));
      setNotice(message);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Perubahan gagal disimpan.");
    } finally {
      setBusy(false);
    }
  }

  async function startExam() {
    if (!exam) return;
    await mutate(
      `/exams/${exam.id}/start`,
      "POST",
      { actual_at: new Date().toISOString(), expected_version: exam.row_version },
      "Ujian dimulai. Draft penilaian kini dapat disimpan.",
    );
  }

  async function saveDraft() {
    if (!exam) return;
    const items = exam.items
      .filter((item) => drafts[item.id]?.score !== "")
      .map((item) => {
        const draft = drafts[item.id] ?? { score: "", notes: "", evidence: "" };
        return {
          exam_item_id: item.id,
          manual_score: Number(draft.score),
          notes: draft.notes || null,
          incidents: draft.evidence
            ? [
                {
                  location_text: draft.evidence,
                  primary_category: "exam_observation",
                  context: null,
                  assistance: "none",
                  self_corrected: false,
                  counted: true,
                  counting_reason: "Bukti penguji",
                  note: draft.notes || null,
                },
              ]
            : [],
        };
      });
    if (items.length === 0) {
      setError("Isi minimal satu skor bulat 1–10 sebelum menyimpan draft.");
      return;
    }
    await mutate(
      `/exams/${exam.id}/assessment-draft`,
      "PUT",
      { items, expected_version: exam.row_version },
      "Draft skor dan bukti tersimpan.",
    );
  }

  async function finalizeExam() {
    if (!exam) return;
    const ids = evidenceIds
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean);
    if (!complete || ids.length === 0) {
      setError("Lengkapi seluruh skor dan minimal satu ID media bukti sebelum finalisasi.");
      return;
    }
    await mutate(
      `/exams/${exam.id}/finalize`,
      "POST",
      {
        actual_at: exam.actual_at ?? new Date().toISOString(),
        manual_score: null,
        examiner_note: examinerNote || null,
        evidence_media_ids: ids,
        expected_version: exam.row_version,
      },
      "Ujian difinalisasi dan Nilai Ujian (Dosen) dihitung dalam satu transaksi.",
    );
  }

  return (
    <AppShell
      accountName={context?.user.display_name ?? "Dosen"}
      initialRole="lecturer"
      organization={context?.active_context?.organization_name ?? "Program Tahfidz"}
    >
      <PageHeader
        breadcrumbs={[
          { href: "/dosen/ujian/pelaksanaan", label: "Pelaksanaan ujian" },
          { label: exam?.participant.display_name ?? "Ujian" },
        ]}
        description="Simpan penilaian per butir sebagai draft, lalu finalisasi setelah bukti dan kebijakan lengkap."
        eyebrow="D03 · Pelaksanaan ujian"
        status={
          <StatusBadge tone={exam?.status === "final" ? "success" : "progress"}>
            {exam?.status === "final" ? "Final" : "Draft aman"}
          </StatusBadge>
        }
        title={exam ? `Ujian ${exam.participant.display_name}` : "Pelaksanaan ujian"}
      />
      {loading ? (
        <FeedbackState
          description="Mengambil paket dan draft penilaian."
          title="Memuat ujian"
          tone="loading"
        />
      ) : null}
      {error ? (
        <FeedbackState description={error} title="Ujian belum dapat diproses" tone="error" />
      ) : null}
      {notice ? <FeedbackState description={notice} title="Perubahan tersimpan" /> : null}
      {!loading && exam ? (
        <WorkSupportLayout
          support={
            <>
              <SupportPanel title="Kesiapan finalisasi">
                {exam.package_policy.blockers.length ? (
                  <ul className={styles.list}>
                    {exam.package_policy.blockers.map((blocker) => (
                      <li key={blocker}>{blockerLabel[blocker] ?? blocker}</li>
                    ))}
                  </ul>
                ) : (
                  <p className={styles.muted}>
                    Kebijakan paket {exam.policy_version} sudah disahkan.
                  </p>
                )}
              </SupportPanel>
              <SupportPanel title="Waktu pelaksanaan">
                <p className={styles.muted}>{dateTimeLabel(exam.actual_at ?? exam.scheduled_at)}</p>
              </SupportPanel>
            </>
          }
        >
          {exam.status === "draft" || exam.status === "scheduled" ? (
            <Card title="Mulai ujian">
              <p className={styles.muted}>
                Paket berisi {exam.items.length} soal. Memulai ujian mengunci waktu aktual.
              </p>
              <div className={styles.actions}>
                <Button disabled={busy || exam.items.length === 0} onClick={() => void startExam()}>
                  Mulai sekarang
                </Button>
              </div>
            </Card>
          ) : null}
          {exam.items.map((item) => (
            <Card
              key={item.id}
              title={`Butir ${item.sequence_no} · ${questionKindLabel[item.kind]}`}
            >
              <p>{item.stimulus}</p>
              <div className={styles.grid}>
                <label>
                  Skor bulat 1–10
                  <input
                    disabled={exam.status === "final"}
                    inputMode="numeric"
                    max="10"
                    min="1"
                    onChange={(event) => updateDraft(item.id, "score", event.target.value)}
                    pattern="([1-9]|10)"
                    required
                    step="1"
                    type="number"
                    value={drafts[item.id]?.score ?? ""}
                  />
                </label>
                <label>
                  Lokasi/bukti jawaban
                  <input
                    disabled={exam.status === "final"}
                    onChange={(event) => updateDraft(item.id, "evidence", event.target.value)}
                    placeholder="Contoh: QS. An-Naba ayat 5"
                    value={drafts[item.id]?.evidence ?? ""}
                  />
                </label>
              </div>
              <label className={styles.field}>
                Catatan penguji
                <textarea
                  disabled={exam.status === "final"}
                  onChange={(event) => updateDraft(item.id, "notes", event.target.value)}
                  rows={3}
                  value={drafts[item.id]?.notes ?? ""}
                />
              </label>
            </Card>
          ))}
          {exam.status === "in_progress" ? (
            <>
              <div className={styles.actions}>
                <Button disabled={busy} onClick={() => void saveDraft()} variant="secondary">
                  Simpan draft semua butir
                </Button>
              </div>
              <Card title="Finalisasi ujian">
                <label className={styles.field}>
                  ID media bukti (pisahkan dengan koma)
                  <textarea
                    onChange={(event) => setEvidenceIds(event.target.value)}
                    placeholder="UUID media yang sudah tersedia"
                    rows={2}
                    value={evidenceIds}
                  />
                </label>
                <label className={styles.field}>
                  Catatan akhir penguji
                  <textarea
                    onChange={(event) => setExaminerNote(event.target.value)}
                    rows={3}
                    value={examinerNote}
                  />
                </label>
                <div className={styles.actions}>
                  <Link href={`/dosen/ujian/${exam.id}/rekap`}>Lihat rekap</Link>
                  <Button
                    disabled={busy || !complete || exam.package_policy.blockers.length > 0}
                    onClick={() => void finalizeExam()}
                  >
                    Finalisasi ujian
                  </Button>
                </div>
              </Card>
            </>
          ) : null}
          {exam.status === "final" ? (
            <Card>
              <Link href={`/dosen/ujian/${exam.id}/rekap`}>
                Buka rekap final dan Nilai Ujian (Dosen)
              </Link>
            </Card>
          ) : null}
        </WorkSupportLayout>
      ) : null}
    </AppShell>
  );
}
