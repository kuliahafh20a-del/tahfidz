"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { AppShell, PageHeader, SupportPanel, WorkSupportLayout } from "@/components/shell";
import { Button, Card, DataTable, FeedbackState, StatusBadge } from "@/components/ui";

import styles from "./workspace.module.css";

type Cohort = {
  id: string;
  name: string;
  start_date: string;
  close_date: string | null;
  status: "draft" | "active" | "closed" | "archived";
  calendar_version: number;
};

type Session = {
  user: { display_name: string };
  active_context: { organization_name: string } | null;
  csrf_token: string;
};

type DeadlineChange = {
  id: string;
  target_id: string;
  old_date: string;
  new_date: string;
  reason: string;
  impact_note: string | null;
  decision_note: string | null;
  status: "pending" | "approved" | "rejected";
  row_version: number;
  created_at: string;
};

type Target = {
  id: string;
  participant: { display_name: string; nim: string };
  theme: { code: string; name: string; part_no: number; part_name: string };
  initial_due_date: string;
  effective_due_date: string;
  status: string;
  pending_change: DeadlineChange | null;
  allowed_actions: string[];
};

type Calendar = {
  cohort: Cohort;
  calendar_version: number;
  targets: Target[];
  history: DeadlineChange[];
  allowed_actions: string[];
};

type Preview = {
  cohort_id: string;
  calendar_version: number;
  affected_count: number;
  earliest_old_date: string;
  latest_old_date: string;
  new_due_date: string;
  requires_approval: boolean;
  impacts: Array<{
    target_id: string;
    participant: Target["participant"];
    theme: Target["theme"];
    old_date: string;
    new_date: string;
    shift_days: number;
  }>;
};

type CursorPage<T> = { items: T[]; page: { has_more: boolean; next_cursor: string | null } };
type ApiEnvelope<T> = { data: T; request_id: string; version: number | null };

class ApiFailure extends Error {
  constructor(
    message: string,
    readonly code?: string,
  ) {
    super(message);
  }
}

const apiRoot = "/api/v1";

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiRoot}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  const body = (await response.json().catch(() => null)) as
    | ApiEnvelope<T>
    | { code?: string; message?: string; detail?: { code?: string; message?: string } }
    | null;
  if (!response.ok) {
    const detail = body && "detail" in body ? body.detail : undefined;
    const code = detail?.code ?? (body && "code" in body ? body.code : undefined);
    const message =
      detail?.message ??
      (body && "message" in body ? body.message : undefined) ??
      "Permintaan gagal diproses.";
    throw new ApiFailure(message, code);
  }
  return (body as ApiEnvelope<T>).data;
}

function dateLabel(value: string): string {
  return new Intl.DateTimeFormat("id-ID", { dateStyle: "medium" }).format(
    new Date(`${value}T00:00:00`),
  );
}

function statusTone(status: DeadlineChange["status"]): "warning" | "success" | "danger" {
  if (status === "approved") return "success";
  if (status === "rejected") return "danger";
  return "warning";
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiFailure && error.code === "VERSION_CONFLICT") {
    return "Kalender diubah oleh pengguna lain. Data terbaru sudah dimuat; silakan tinjau ulang pilihan Anda.";
  }
  return error instanceof Error ? error.message : "Data kalender tidak tersedia.";
}

export function DepartmentCalendarWorkspace() {
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [cohortId, setCohortId] = useState("");
  const [calendar, setCalendar] = useState<Calendar | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [preview, setPreview] = useState<Preview | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    void Promise.all([
      apiRequest<Session>("/auth/session"),
      apiRequest<CursorPage<Cohort>>("/department/cohorts?limit=100"),
    ])
      .then(async ([loadedSession, cohortPage]) => {
        const firstCohort = cohortPage.items[0];
        const loadedCalendar = firstCohort
          ? await apiRequest<Calendar>(`/department/cohorts/${firstCohort.id}/calendar`)
          : null;
        if (!active) return;
        setSession(loadedSession);
        setCohorts(cohortPage.items);
        setCohortId(firstCohort?.id ?? "");
        setCalendar(loadedCalendar);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (active) setError(errorMessage(caught));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reloadKey]);

  const pending = useMemo(
    () => calendar?.history.filter((change) => change.status === "pending") ?? [],
    [calendar],
  );

  async function loadCalendar(nextCohortId: string): Promise<void> {
    setLoading(true);
    setError(null);
    setNotice(null);
    setPreview(null);
    setSelectedIds(new Set());
    setCohortId(nextCohortId);
    setCalendar(null);
    try {
      setCalendar(
        nextCohortId
          ? await apiRequest<Calendar>(`/department/cohorts/${nextCohortId}/calendar`)
          : null,
      );
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }

  async function refreshCalendar(): Promise<void> {
    if (!cohortId) return;
    setCalendar(await apiRequest<Calendar>(`/department/cohorts/${cohortId}/calendar`));
  }

  function toggleTarget(targetId: string): void {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(targetId)) next.delete(targetId);
      else next.add(targetId);
      return next;
    });
    setPreview(null);
  }

  function selectAll(): void {
    if (!calendar) return;
    const selectable = calendar.targets.filter((target) => target.pending_change === null);
    setSelectedIds(
      selectedIds.size === selectable.length ? new Set() : new Set(selectable.map(({ id }) => id)),
    );
    setPreview(null);
  }

  function proposalPayload(form: HTMLFormElement) {
    const values = new FormData(form);
    return {
      target_ids: [...selectedIds],
      new_due_date: values.get("new_due_date"),
      reason: values.get("reason"),
      impact_note: values.get("impact_note") || null,
      expected_version: calendar?.calendar_version,
    };
  }

  async function reviewProposal(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!calendar || !session || selectedIds.size === 0) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setPreview(
        await apiRequest<Preview>(`/department/cohorts/${cohortId}/deadline-changes/preview`, {
          method: "POST",
          headers: { "X-CSRF-Token": session.csrf_token },
          body: JSON.stringify(proposalPayload(event.currentTarget)),
        }),
      );
    } catch (caught) {
      setError(errorMessage(caught));
      if (caught instanceof ApiFailure && caught.code === "VERSION_CONFLICT") {
        await refreshCalendar().catch(() => undefined);
      }
    } finally {
      setBusy(false);
    }
  }

  async function submitProposal(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!calendar || !session || !preview) return;
    const form = event.currentTarget;
    setBusy(true);
    setError(null);
    try {
      await apiRequest(`/department/cohorts/${cohortId}/deadline-changes`, {
        method: "POST",
        headers: {
          "Idempotency-Key": crypto.randomUUID(),
          "X-CSRF-Token": session.csrf_token,
        },
        body: JSON.stringify(proposalPayload(form)),
      });
      setNotice("Usulan perubahan tenggat tercatat dan menunggu keputusan.");
      setPreview(null);
      setSelectedIds(new Set());
      form.reset();
      await refreshCalendar();
    } catch (caught) {
      setError(errorMessage(caught));
      if (caught instanceof ApiFailure && caught.code === "VERSION_CONFLICT") {
        await refreshCalendar().catch(() => undefined);
      }
    } finally {
      setBusy(false);
    }
  }

  async function decide(change: DeadlineChange, approve: boolean): Promise<void> {
    if (!calendar || !session) return;
    setBusy(true);
    setError(null);
    try {
      await apiRequest(
        `/department/deadline-changes/${change.id}/${approve ? "approve" : "reject"}`,
        {
          method: "POST",
          headers: {
            "Idempotency-Key": crypto.randomUUID(),
            "X-CSRF-Token": session.csrf_token,
          },
          body: JSON.stringify({
            expected_version: change.row_version,
            decision_note: approve
              ? "Disetujui setelah peninjauan dampak kalender."
              : "Ditolak setelah peninjauan dampak kalender.",
          }),
        },
      );
      setNotice(
        approve
          ? "Perubahan disetujui dan tenggat efektif telah diperbarui."
          : "Usulan perubahan ditolak; tenggat efektif tidak berubah.",
      );
      await refreshCalendar();
    } catch (caught) {
      setError(errorMessage(caught));
      await refreshCalendar().catch(() => undefined);
    } finally {
      setBusy(false);
    }
  }

  const targetRows =
    calendar?.targets.map((target) => [
      <label className={styles.targetIdentity} key={`${target.id}-identity`}>
        <input
          checked={selectedIds.has(target.id)}
          disabled={target.pending_change !== null || busy}
          onChange={() => toggleTarget(target.id)}
          type="checkbox"
        />
        <span>
          <strong>{target.participant.display_name}</strong>
          <small>{target.participant.nim}</small>
        </span>
      </label>,
      <span key={`${target.id}-theme`}>
        <strong>{target.theme.code}</strong> · {target.theme.name}
      </span>,
      dateLabel(target.initial_due_date),
      <span className={styles.dueDate} key={`${target.id}-due`}>
        {dateLabel(target.effective_due_date)}
        {target.pending_change ? <StatusBadge tone="warning">Menunggu</StatusBadge> : null}
      </span>,
    ]) ?? [];

  return (
    <AppShell
      accountName={session?.user.display_name ?? "Admin Jurusan"}
      initialRole="department_admin"
      organization={session?.active_context?.organization_name ?? "Lingkup jurusan aktif"}
    >
      <PageHeader
        breadcrumbs={[{ href: "/", label: "Beranda" }, { label: "Kalender angkatan" }]}
        description="Tinjau dampak, ajukan, dan putuskan perubahan tenggat tanpa menghapus jadwal awal."
        eyebrow="J02 · Administrasi jurusan"
        status={
          calendar ? (
            <StatusBadge tone="neutral">Versi {calendar.calendar_version}</StatusBadge>
          ) : null
        }
        title="Kalender angkatan"
      />

      {loading ? (
        <FeedbackState
          description="Mengambil angkatan, target, dan riwayat perubahan."
          title="Memuat kalender"
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
          title="Kalender belum dapat diproses"
          tone="error"
        />
      ) : null}
      {notice ? <FeedbackState description={notice} title="Perubahan tersimpan" /> : null}

      {!loading && cohorts.length === 0 ? (
        <FeedbackState
          description="Buat angkatan dan target terlebih dahulu sebelum menyusun perubahan tenggat."
          title="Belum ada angkatan"
        />
      ) : null}

      {cohorts.length > 0 ? (
        <div className={styles.cohortPicker}>
          <label htmlFor="cohort">Angkatan</label>
          <select
            disabled={busy}
            id="cohort"
            onChange={(event) => void loadCalendar(event.target.value)}
            value={cohortId}
          >
            {cohorts.map((cohort) => (
              <option key={cohort.id} value={cohort.id}>
                {cohort.name}
              </option>
            ))}
          </select>
          <span>{calendar ? `${calendar.targets.length} target` : "Belum dipilih"}</span>
        </div>
      ) : null}

      {calendar ? (
        <WorkSupportLayout
          support={
            <>
              <SupportPanel title="Alur persetujuan">
                <ol className={styles.steps}>
                  <li>Pilih target dan isi tenggat baru.</li>
                  <li>Tinjau pergeseran tanggal sebelum mengajukan.</li>
                  <li>Setujui atau tolak usulan yang menunggu.</li>
                </ol>
              </SupportPanel>
              <SupportPanel title="Jejak jadwal">
                <p className={styles.supportCopy}>
                  Tenggat awal selalu dipertahankan. Hanya tenggat efektif yang berubah setelah
                  persetujuan dan seluruh keputusan dicatat dalam audit.
                </p>
              </SupportPanel>
            </>
          }
        >
          <Card className={styles.calendarCard} title="Target peserta">
            <div className={styles.tableActions}>
              <p>Pilih satu atau beberapa tema untuk perubahan yang sama.</p>
              <Button
                disabled={busy || calendar.targets.length === 0}
                onClick={selectAll}
                variant="tertiary"
              >
                {selectedIds.size > 0 ? "Kosongkan pilihan" : "Pilih semua tersedia"}
              </Button>
            </div>
            {calendar.targets.length === 0 ? (
              <FeedbackState
                description="Generate target untuk peserta angkatan ini terlebih dahulu."
                title="Target belum tersedia"
              />
            ) : (
              <DataTable
                caption={`${calendar.cohort.name} · ${calendar.targets.length} target`}
                headings={["Peserta", "Tema", "Tenggat awal", "Tenggat efektif"]}
                rows={targetRows}
              />
            )}
          </Card>

          <Card title="Ajukan perubahan tenggat">
            <form
              className={styles.proposalForm}
              onSubmit={(event) => void (preview ? submitProposal(event) : reviewProposal(event))}
            >
              <label>
                Tenggat baru
                <input name="new_due_date" readOnly={preview !== null} required type="date" />
              </label>
              <label>
                Alasan perubahan
                <textarea name="reason" readOnly={preview !== null} required rows={3} />
              </label>
              <label>
                Catatan dampak
                <textarea name="impact_note" readOnly={preview !== null} rows={3} />
              </label>
              <div className={styles.formActions}>
                {preview ? (
                  <Button
                    disabled={busy}
                    onClick={() => setPreview(null)}
                    type="button"
                    variant="secondary"
                  >
                    Ubah usulan
                  </Button>
                ) : null}
                <Button disabled={busy || selectedIds.size === 0} type="submit">
                  {preview ? "Ajukan untuk persetujuan" : "Tinjau dampak"}
                </Button>
              </div>
            </form>
            {preview ? (
              <div className={styles.preview}>
                <div className={styles.previewSummary}>
                  <strong>{preview.affected_count} target terdampak</strong>
                  <span>
                    Rentang awal {dateLabel(preview.earliest_old_date)}–
                    {dateLabel(preview.latest_old_date)}
                  </span>
                </div>
                <DataTable
                  caption="Pratinjau pergeseran tenggat"
                  headings={["Peserta", "Tema", "Lama → baru", "Pergeseran"]}
                  rows={preview.impacts.map((impact) => [
                    `${impact.participant.display_name} · ${impact.participant.nim}`,
                    `${impact.theme.code} · ${impact.theme.name}`,
                    `${dateLabel(impact.old_date)} → ${dateLabel(impact.new_date)}`,
                    `${impact.shift_days >= 0 ? "+" : ""}${impact.shift_days} hari`,
                  ])}
                />
              </div>
            ) : null}
          </Card>

          <Card title={`Menunggu keputusan (${pending.length})`}>
            {pending.length === 0 ? (
              <FeedbackState
                description="Usulan baru akan muncul di sini dan tenggat belum berubah sebelum disetujui."
                title="Tidak ada usulan tertunda"
              />
            ) : (
              <div className={styles.changeList}>
                {pending.map((change) => (
                  <article key={change.id}>
                    <div>
                      <StatusBadge tone="warning">Menunggu</StatusBadge>
                      <strong>
                        {dateLabel(change.old_date)} → {dateLabel(change.new_date)}
                      </strong>
                      <p>{change.reason}</p>
                      {change.impact_note ? <small>{change.impact_note}</small> : null}
                    </div>
                    <div className={styles.decisionActions}>
                      <Button
                        disabled={busy}
                        onClick={() => void decide(change, false)}
                        variant="danger"
                      >
                        Tolak
                      </Button>
                      <Button disabled={busy} onClick={() => void decide(change, true)}>
                        Setujui
                      </Button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </Card>

          <Card title="Riwayat perubahan">
            {calendar.history.length === 0 ? (
              <p className={styles.emptyCopy}>Belum ada perubahan tenggat pada angkatan ini.</p>
            ) : (
              <DataTable
                caption="Keputusan perubahan tenggat"
                headings={["Status", "Tanggal", "Alasan", "Catatan keputusan"]}
                rows={calendar.history.map((change) => [
                  <StatusBadge key={`${change.id}-status`} tone={statusTone(change.status)}>
                    {change.status}
                  </StatusBadge>,
                  `${dateLabel(change.old_date)} → ${dateLabel(change.new_date)}`,
                  change.reason,
                  change.decision_note ?? "Belum diputuskan",
                ])}
              />
            )}
          </Card>
        </WorkSupportLayout>
      ) : null}
    </AppShell>
  );
}
