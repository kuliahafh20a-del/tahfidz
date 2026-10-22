"use client";

import { FormEvent, useEffect, useState } from "react";

import styles from "./workspace.module.css";

type Cohort = {
  id: string;
  name: string;
  status: "draft" | "active" | "closed" | "archived";
  start_date: string;
  close_date: string | null;
};

type UserReference = {
  id: string;
  name: string;
  login_identifier: string;
};

type Assignment = {
  id: string;
  role: "mentor" | "lecturer";
  staff: UserReference;
  valid_from: string;
  valid_to: string | null;
  reason: string | null;
};

type Enrollment = {
  id: string;
  cohort_id: string;
  user: UserReference;
  nim_snapshot: string;
  status: "active" | "completed" | "withdrawn" | "inactive";
  joined_at: string;
};

type EnrollmentDetail = Enrollment & { assignments: Assignment[] };

const apiRoot = "/api/v1";

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiRoot}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as {
      detail?: { code?: string; message?: string };
    } | null;
    throw new Error(error?.detail?.message ?? error?.detail?.code ?? "Permintaan gagal diproses.");
  }
  return (await response.json()) as T;
}

function dateLabel(value: string | null): string {
  if (value === null) return "Masih aktif";
  return new Intl.DateTimeFormat("id-ID", { dateStyle: "medium" }).format(new Date(value));
}

async function loadWorkspace(): Promise<{
  cohorts: Cohort[];
  enrollments: Enrollment[];
  csrfToken: string;
}> {
  const [session, cohorts, enrollments] = await Promise.all([
    apiRequest<{ csrf_token: string }>("/auth/session"),
    apiRequest<Cohort[]>("/department/cohorts"),
    apiRequest<Enrollment[]>("/department/enrollments"),
  ]);
  return { cohorts, enrollments, csrfToken: session.csrf_token };
}

export function ParticipantAssignmentWorkspace() {
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [selected, setSelected] = useState<EnrollmentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [csrfToken, setCsrfToken] = useState<string | null>(null);

  async function refresh(): Promise<void> {
    const workspace = await loadWorkspace();
    setCohorts(workspace.cohorts);
    setEnrollments(workspace.enrollments);
    setCsrfToken(workspace.csrfToken);
  }

  useEffect(() => {
    let active = true;
    void loadWorkspace()
      .then((workspace) => {
        if (!active) return;
        setCohorts(workspace.cohorts);
        setEnrollments(workspace.enrollments);
        setCsrfToken(workspace.csrfToken);
      })
      .catch((error: unknown) => {
        if (active) setMessage(error instanceof Error ? error.message : "Data tidak tersedia.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function openEnrollment(enrollmentId: string): Promise<void> {
    try {
      setMessage(null);
      setSelected(await apiRequest<EnrollmentDetail>(`/department/enrollments/${enrollmentId}`));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Detail peserta tidak tersedia.");
    }
  }

  async function createEnrollment(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      if (csrfToken === null) throw new Error("Session belum siap. Muat ulang halaman.");
      await apiRequest<Enrollment>("/department/enrollments", {
        method: "POST",
        headers: { "X-CSRF-Token": csrfToken },
        body: JSON.stringify({
          user_id: form.get("user_id"),
          cohort_id: form.get("cohort_id"),
          nim_snapshot: form.get("nim_snapshot"),
        }),
      });
      event.currentTarget.reset();
      setMessage("Peserta berhasil didaftarkan.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Peserta gagal didaftarkan.");
    }
  }

  async function createAssignment(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (selected === null) return;
    const form = new FormData(event.currentTarget);
    const localStart = String(form.get("valid_from"));
    try {
      if (csrfToken === null) throw new Error("Session belum siap. Muat ulang halaman.");
      await apiRequest<Assignment>(`/department/enrollments/${selected.id}/assignments`, {
        method: "POST",
        headers: { "X-CSRF-Token": csrfToken },
        body: JSON.stringify({
          role: form.get("role"),
          assignee_user_id: form.get("assignee_user_id"),
          valid_from: new Date(localStart).toISOString(),
          valid_to: null,
          reason: form.get("reason") || null,
        }),
      });
      event.currentTarget.reset();
      setMessage("Penugasan baru aktif dan riwayat sebelumnya dipertahankan.");
      await openEnrollment(selected.id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Penugasan gagal dibuat.");
    }
  }

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>J01 · Administrasi jurusan</p>
          <h1 className={styles.title}>Peserta dan penugasan</h1>
          <p className={styles.subtitle}>
            Kelola keanggotaan angkatan serta riwayat Mentor dan Dosen tanpa menimpa data lama.
          </p>
        </div>
        <span className={styles.scopeBadge}>Lingkup jurusan aktif</span>
      </header>

      {message ? (
        <p className={styles.notice} role="status">
          {message}
        </p>
      ) : null}

      <section className={styles.summary} aria-label="Ringkasan peserta">
        <article>
          <strong>{loading ? "…" : enrollments.length}</strong>
          <span>Peserta</span>
        </article>
        <article>
          <strong>{loading ? "…" : cohorts.length}</strong>
          <span>Angkatan</span>
        </article>
        <article>
          <strong>
            {loading ? "…" : enrollments.filter((item) => item.status === "active").length}
          </strong>
          <span>Aktif</span>
        </article>
      </section>

      <div className={styles.grid}>
        <section className={styles.panel} aria-labelledby="participant-list-title">
          <div className={styles.panelHeading}>
            <div>
              <p className={styles.kicker}>Daftar peserta</p>
              <h2 id="participant-list-title">Peserta dalam lingkup Anda</h2>
            </div>
          </div>
          {loading ? <p className={styles.empty}>Memuat peserta…</p> : null}
          {!loading && enrollments.length === 0 ? (
            <p className={styles.empty}>
              Belum ada peserta. Gunakan formulir pendaftaran di bawah.
            </p>
          ) : null}
          <div className={styles.participantList}>
            {enrollments.map((item) => (
              <button
                className={styles.participant}
                key={item.id}
                onClick={() => void openEnrollment(item.id)}
                type="button"
              >
                <span className={styles.avatar}>{item.user.name.slice(0, 1).toUpperCase()}</span>
                <span className={styles.participantIdentity}>
                  <strong>{item.user.name}</strong>
                  <small>{item.nim_snapshot}</small>
                </span>
                <span className={styles.status}>{item.status}</span>
              </button>
            ))}
          </div>

          <form className={styles.form} onSubmit={(event) => void createEnrollment(event)}>
            <h3>Daftarkan peserta</h3>
            <label>
              Angkatan
              <select name="cohort_id" required>
                <option value="">Pilih angkatan</option>
                {cohorts.map((cohort) => (
                  <option key={cohort.id} value={cohort.id}>
                    {cohort.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              ID akun peserta
              <input name="user_id" placeholder="UUID akun" required />
            </label>
            <label>
              NIM
              <input name="nim_snapshot" placeholder="Contoh: 20270001" required />
            </label>
            <button className={styles.primaryAction} type="submit">
              Daftarkan peserta
            </button>
          </form>
        </section>

        <aside className={styles.panel} aria-labelledby="assignment-title">
          <div className={styles.panelHeading}>
            <div>
              <p className={styles.kicker}>Riwayat penugasan</p>
              <h2 id="assignment-title">{selected?.user.name ?? "Pilih peserta"}</h2>
            </div>
          </div>
          {selected === null ? (
            <p className={styles.empty}>
              Pilih peserta untuk meninjau Mentor, Dosen, dan masa berlaku.
            </p>
          ) : (
            <>
              <dl className={styles.identityDetails}>
                <div>
                  <dt>NIM</dt>
                  <dd>{selected.nim_snapshot}</dd>
                </div>
                <div>
                  <dt>Akun</dt>
                  <dd>{selected.user.login_identifier}</dd>
                </div>
              </dl>
              <ol className={styles.timeline}>
                {selected.assignments.map((item) => (
                  <li key={item.id}>
                    <span className={styles.timelineDot} />
                    <div>
                      <strong>
                        {item.role === "mentor" ? "Mentor" : "Dosen"} · {item.staff.name}
                      </strong>
                      <p>
                        {dateLabel(item.valid_from)} — {dateLabel(item.valid_to)}
                      </p>
                      {item.reason ? <small>{item.reason}</small> : null}
                    </div>
                  </li>
                ))}
              </ol>
              <form className={styles.form} onSubmit={(event) => void createAssignment(event)}>
                <h3>Buat penugasan baru</h3>
                <label>
                  Peran
                  <select name="role" required>
                    <option value="mentor">Mentor</option>
                    <option value="lecturer">Dosen</option>
                  </select>
                </label>
                <label>
                  ID akun petugas
                  <input name="assignee_user_id" placeholder="UUID petugas" required />
                </label>
                <label>
                  Berlaku mulai
                  <input name="valid_from" type="datetime-local" required />
                </label>
                <label>
                  Alasan
                  <textarea
                    name="reason"
                    placeholder="Penugasan awal atau rotasi petugas"
                    rows={3}
                  />
                </label>
                <button className={styles.primaryAction} type="submit">
                  Tinjau penugasan
                </button>
              </form>
            </>
          )}
        </aside>
      </div>
    </main>
  );
}
