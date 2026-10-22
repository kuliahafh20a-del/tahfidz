"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import styles from "./auth-card.module.css";

type AuthMode = "login" | "recovery";

type SessionPayload = {
  active_context: { role: string; organization_id: string } | null;
};

type ApiEnvelope<T> = {
  data: T;
  request_id: string;
  version: number | null;
};

type ApiError = {
  code?: string;
  message?: string;
  request_id?: string;
};

async function postJson<T>(path: string, body: object): Promise<T> {
  const response = await fetch(`/api/v1/auth${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = (await response.json().catch(() => null)) as ApiEnvelope<T> | ApiError | null;
  if (!response.ok) {
    const error = payload as ApiError | null;
    throw new Error(error?.message ?? error?.code ?? "Permintaan tidak dapat diproses.");
  }
  return (payload as ApiEnvelope<T>).data;
}

export function AuthCard({ mode }: { mode: AuthMode }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function login(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const session = await postJson<SessionPayload>("/login", {
        identifier: form.get("identifier"),
        password: form.get("password"),
      });
      router.replace(
        session.active_context?.role === "department_admin" ? "/department/participants" : "/",
      );
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Gagal masuk.");
    } finally {
      setBusy(false);
    }
  }

  async function requestRecovery(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const result = await postJson<{ message: string }>("/password-recovery", {
        identifier: form.get("identifier"),
      });
      setMessage(result.message);
      event.currentTarget.reset();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Pemulihan belum dapat diproses.");
    } finally {
      setBusy(false);
    }
  }

  async function resetPassword(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("new_password"));
    if (password !== form.get("confirm_password")) {
      setError("Konfirmasi kata sandi tidak sama.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await postJson<{ message: string }>("/password-reset", {
        token: form.get("token"),
        new_password: password,
      });
      setMessage(result.message);
      event.currentTarget.reset();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Token pemulihan tidak dapat digunakan.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.story} aria-labelledby="auth-story-title">
        <div className={styles.brand}>
          <span className={styles.mark}>YQ</span>
          YAQin
        </div>
        <div className={styles.storyCopy}>
          <p className={styles.eyebrow}>Yakin · Amalin · Mutqin</p>
          <h1 id="auth-story-title">Hafalan terarah, pendampingan bermakna.</h1>
          <p>
            Satu ruang aman untuk peserta, mentor, dosen, dan pengelola menjaga perjalanan Juz 30
            tetap terukur dan manusiawi.
          </p>
          <div className={styles.principles} aria-label="Prinsip YAQin">
            <span>Aman</span>
            <span>Terukur</span>
            <span>Berkelanjutan</span>
          </div>
        </div>
      </section>

      <section className={styles.formArea}>
        <div className={styles.card}>
          <h2>{mode === "login" ? "Selamat datang" : "Pulihkan akun"}</h2>
          <p className={styles.intro}>
            {mode === "login"
              ? "Masukkan identitas akun yang diberikan pengelola institusi."
              : "Kami selalu memberi respons yang sama untuk menjaga kerahasiaan akun."}
          </p>
          {message ? (
            <p className={styles.notice} role="status">
              {message}
            </p>
          ) : null}
          {error ? (
            <p className={styles.error} role="alert">
              {error}
            </p>
          ) : null}

          {mode === "login" ? (
            <form className={styles.form} onSubmit={(event) => void login(event)}>
              <label>
                Email atau identifier
                <input autoComplete="username" name="identifier" required />
              </label>
              <label>
                Kata sandi
                <input autoComplete="current-password" name="password" type="password" required />
              </label>
              <button className={styles.primary} disabled={busy} type="submit">
                {busy ? "Memeriksa…" : "Masuk dengan aman"}
              </button>
            </form>
          ) : (
            <>
              <form className={styles.form} onSubmit={(event) => void requestRecovery(event)}>
                <label>
                  Email atau identifier
                  <input autoComplete="username" name="identifier" required />
                </label>
                <button className={styles.primary} disabled={busy} type="submit">
                  Minta instruksi pemulihan
                </button>
              </form>
              <div className={styles.divider} />
              <form className={styles.form} onSubmit={(event) => void resetPassword(event)}>
                <label>
                  Token pemulihan
                  <input autoComplete="one-time-code" name="token" required />
                </label>
                <label>
                  Kata sandi baru
                  <input
                    autoComplete="new-password"
                    minLength={12}
                    name="new_password"
                    required
                    type="password"
                  />
                </label>
                <label>
                  Ulangi kata sandi baru
                  <input
                    autoComplete="new-password"
                    minLength={12}
                    name="confirm_password"
                    required
                    type="password"
                  />
                </label>
                <button className={styles.primary} disabled={busy} type="submit">
                  Simpan kata sandi baru
                </button>
              </form>
            </>
          )}

          <p className={styles.switcher}>
            {mode === "login" ? (
              <Link href="/recovery">Lupa kata sandi?</Link>
            ) : (
              <Link href="/login">Kembali ke halaman masuk</Link>
            )}
          </p>
        </div>
      </section>
    </main>
  );
}
