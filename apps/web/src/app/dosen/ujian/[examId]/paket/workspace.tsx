"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { AppShell, PageHeader, SupportPanel, WorkSupportLayout } from "@/components/shell";
import { Button, Card, FeedbackState, StatusBadge } from "@/components/ui";
import { Exam, QuestionVersion, questionKindLabel } from "@/lib/exams";
import { apiRequest, SessionContext } from "@/lib/mentoring";

import styles from "./workspace.module.css";

const blockerLabel: Record<string, string> = {
  exam_package_policy_not_approved: "Jumlah dan bobot soal belum disahkan",
  exam_item_count_mismatch: "Jumlah soal belum sesuai kebijakan",
  exam_item_weights_incomplete: "Bobot soal belum lengkap",
  exam_item_weight_total_mismatch: "Total bobot belum sesuai kebijakan",
};

export function ExamPackageWorkspace({ examId }: { examId: string }) {
  const [context, setContext] = useState<SessionContext | null>(null);
  const [exam, setExam] = useState<Exam | null>(null);
  const [questions, setQuestions] = useState<QuestionVersion[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [questionId, setQuestionId] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    void Promise.all([
      apiRequest<SessionContext>("/auth/session"),
      apiRequest<Exam>(`/exams/${examId}`),
      apiRequest<QuestionVersion[]>("/lecturer/questions"),
    ])
      .then(([loadedContext, loadedExam, loadedQuestions]) => {
        if (!active) return;
        setContext(loadedContext);
        setExam(loadedExam);
        setQuestions(loadedQuestions);
        setSelectedIds(loadedExam.items.map((item) => item.question_version_id));
        setQuestionId(loadedQuestions[0]?.id ?? "");
        setError(null);
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof Error ? caught.message : "Paket tidak tersedia.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [examId, reloadKey]);

  const selectedQuestions = useMemo(
    () =>
      selectedIds
        .map((id) => questions.find((item) => item.id === id))
        .filter((item): item is QuestionVersion => Boolean(item)),
    [questions, selectedIds],
  );

  async function saveItems() {
    if (!context || !exam || selectedIds.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await apiRequest<Exam>(`/exams/${exam.id}/items`, {
        method: "PUT",
        headers: { "Idempotency-Key": crypto.randomUUID(), "X-CSRF-Token": context.csrf_token },
        body: JSON.stringify({
          items: selectedIds.map((id) => ({ question_version_id: id, weight: null })),
          expected_version: exam.row_version,
        }),
      });
      setExam(updated);
      setNotice("Draft paket soal tersimpan sebagai snapshot berversi.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Paket gagal disimpan.");
    } finally {
      setBusy(false);
    }
  }

  async function createQuestion(form: HTMLFormElement) {
    if (!context) return;
    setBusy(true);
    setError(null);
    try {
      const values = new FormData(form);
      const created = await apiRequest<QuestionVersion>("/lecturer/questions", {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID(), "X-CSRF-Token": context.csrf_token },
        body: JSON.stringify({
          kind: values.get("kind"),
          stimulus: values.get("stimulus"),
          scope: JSON.parse(String(values.get("scope"))),
          answer_reference: JSON.parse(String(values.get("answer_reference"))),
        }),
      });
      setQuestions((current) => [...current, created]);
      setSelectedIds((current) => [...current, created.id]);
      setQuestionId(created.id);
      setNotice("Soal Dosen versi pertama dibuat dan ditambahkan ke susunan lokal.");
      form.reset();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Soal gagal dibuat. Pastikan JSON valid.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell
      accountName={context?.user.display_name ?? "Dosen"}
      initialRole="lecturer"
      organization={context?.active_context?.organization_name ?? "Program Tahfidz"}
    >
      <PageHeader
        breadcrumbs={[
          { href: "/dosen/ujian", label: "Antrean ujian" },
          { label: exam?.participant.display_name ?? "Paket soal" },
        ]}
        description="Susun snapshot soal dari sumber aplikasi atau Dosen. Acuan jawaban hanya terlihat dalam scope penguji."
        eyebrow="D02 · Paket soal"
        status={
          <StatusBadge tone={exam?.package_policy.blockers.length ? "warning" : "success"}>
            {exam?.package_policy.blockers.length ? "Keputusan terbuka" : "Paket siap"}
          </StatusBadge>
        }
        title={exam ? `Paket ujian ${exam.participant.display_name}` : "Paket soal"}
      />
      {loading ? (
        <FeedbackState
          description="Mengambil draft ujian dan bank soal berizin."
          title="Memuat paket"
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
          title="Paket belum dapat diproses"
          tone="error"
        />
      ) : null}
      {notice ? <FeedbackState description={notice} title="Perubahan tersimpan" /> : null}
      {!loading && !error && exam ? (
        <WorkSupportLayout
          support={
            <>
              <SupportPanel title="Status kebijakan">
                {exam.package_policy.blockers.length ? (
                  <ul className={styles.blockers}>
                    {exam.package_policy.blockers.map((item) => (
                      <li key={item}>{blockerLabel[item] ?? item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className={styles.supportCopy}>
                    Jumlah dan total bobot paket telah sesuai policy {exam.policy_version}.
                  </p>
                )}
              </SupportPanel>
              <SupportPanel title="Privasi acuan">
                <p className={styles.supportCopy}>
                  Acuan jawaban tersimpan dalam snapshot historis dan hanya dikirim melalui endpoint
                  Dosen yang memiliki assignment aktif.
                </p>
              </SupportPanel>
            </>
          }
        >
          <Card title={`Susunan paket (${selectedQuestions.length})`}>
            <div className={styles.addRow}>
              <select onChange={(event) => setQuestionId(event.target.value)} value={questionId}>
                <option value="">Pilih soal</option>
                {questions
                  .filter((item) => !selectedIds.includes(item.id))
                  .map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.source === "application" ? "Aplikasi" : "Dosen"} ·{" "}
                      {questionKindLabel[item.kind]} · v{item.version_no}
                    </option>
                  ))}
              </select>
              <Button
                disabled={!questionId || selectedIds.includes(questionId)}
                onClick={() => setSelectedIds((current) => [...current, questionId])}
                type="button"
                variant="secondary"
              >
                Tambah ke paket
              </Button>
            </div>
            {selectedQuestions.length === 0 ? (
              <FeedbackState
                description="Pilih soal dari bank atau buat soal Dosen."
                title="Paket masih kosong"
              />
            ) : (
              <ol className={styles.items}>
                {selectedQuestions.map((item) => (
                  <li key={item.id}>
                    <div>
                      <strong>{questionKindLabel[item.kind]}</strong>
                      <p>{item.stimulus}</p>
                      <small>
                        {item.source === "application" ? "Aplikasi" : "Dosen"} · versi{" "}
                        {item.version_no}
                      </small>
                      <details>
                        <summary>Lihat acuan privat</summary>
                        <pre>{JSON.stringify(item.answer_reference, null, 2)}</pre>
                      </details>
                    </div>
                    <Button
                      onClick={() =>
                        setSelectedIds((current) => current.filter((id) => id !== item.id))
                      }
                      type="button"
                      variant="secondary"
                    >
                      Hapus
                    </Button>
                  </li>
                ))}
              </ol>
            )}
            <div className={styles.actions}>
              <Button disabled={busy || selectedIds.length === 0} onClick={() => void saveItems()}>
                Simpan draft paket
              </Button>
            </div>
          </Card>
          <Card title="Buat soal Dosen">
            <form
              className={styles.form}
              onSubmit={(event: FormEvent<HTMLFormElement>) => {
                event.preventDefault();
                void createQuestion(event.currentTarget);
              }}
            >
              <label>
                Jenis soal
                <select name="kind">
                  <option value="continue_verses">Sambung ayat</option>
                  <option value="surah_order">Urutan surah</option>
                  <option value="recitation">Tilawah</option>
                </select>
              </label>
              <label>
                Stimulus
                <textarea name="stimulus" required rows={3} />
              </label>
              <label>
                Cakupan (JSON)
                <textarea defaultValue={'{"juz": 30}'} name="scope" required rows={3} />
              </label>
              <label>
                Acuan jawaban privat (JSON)
                <textarea
                  defaultValue={'{"notes": ""}'}
                  name="answer_reference"
                  required
                  rows={4}
                />
              </label>
              <div className={styles.actions}>
                <Button disabled={busy} type="submit">
                  Buat versi soal
                </Button>
              </div>
            </form>
          </Card>
        </WorkSupportLayout>
      ) : null}
    </AppShell>
  );
}
