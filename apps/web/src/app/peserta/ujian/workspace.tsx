"use client";

import { useEffect, useState } from "react";

import { AppShell, PageHeader, SupportPanel, WorkSupportLayout } from "@/components/shell";
import { Button, Card, DataTable, FeedbackState, StatusBadge } from "@/components/ui";
import {
  componentStatusLabel,
  GradeHistory,
  GradeSnapshot,
  missingRequirementLabel,
} from "@/lib/grading";
import { ApiFailure, apiRequest, dateTimeLabel, SessionContext } from "@/lib/mentoring";

import styles from "./workspace.module.css";

const statusLabel: Record<GradeSnapshot["status"], string> = {
  incomplete: "Belum lengkap",
  ready_for_exam: "Siap ujian",
  awaiting_exam: "Menunggu ujian",
  awaiting_components: "Menunggu komponen",
  graduated: "Lulus",
  not_graduated: "Belum lulus",
  needs_review: "Perlu peninjauan",
};

export function ParticipantGradeWorkspace() {
  const [context, setContext] = useState<SessionContext | null>(null);
  const [snapshot, setSnapshot] = useState<GradeSnapshot | null>(null);
  const [history, setHistory] = useState<GradeSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void apiRequest<SessionContext>("/auth/session")
      .then(async (loadedContext) => {
        try {
          const [latest, loadedHistory] = await Promise.all([
            apiRequest<GradeSnapshot>("/me/grades"),
            apiRequest<GradeHistory>("/me/grades/history"),
          ]);
          return { loadedContext, latest, loadedHistory };
        } catch (caught) {
          if (caught instanceof ApiFailure && caught.code === "GRADE_SNAPSHOT_NOT_FOUND") {
            return { loadedContext, latest: null, loadedHistory: { items: [] } };
          }
          throw caught;
        }
      })
      .then(({ loadedContext, latest, loadedHistory }) => {
        if (!active) return;
        setContext(loadedContext);
        setSnapshot(latest);
        setHistory(loadedHistory.items);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "Rekap nilai belum dapat dimuat.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function publish() {
    if (!context) return;
    setPublishing(true);
    try {
      const published = await apiRequest<GradeSnapshot>("/me/grades/publish", {
        method: "POST",
        headers: { "X-CSRF-Token": context.csrf_token },
      });
      setSnapshot(published);
      const loadedHistory = await apiRequest<GradeHistory>("/me/grades/history");
      setHistory(loadedHistory.items);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Snapshot nilai gagal diterbitkan.");
    } finally {
      setPublishing(false);
    }
  }

  const components = snapshot
    ? (["k", "m", "d"] as const).map((key) => ({ key, ...snapshot.components[key] }))
    : [];

  return (
    <AppShell
      accountName={context?.user.display_name ?? "Peserta"}
      initialRole="participant"
      organization={context?.active_context?.organization_name ?? "Program Tahfidz"}
    >
      <PageHeader
        breadcrumbs={[{ href: "/peserta", label: "Beranda" }, { label: "Ujian dan nilai" }]}
        description="Pantau kesiapan ujian, komponen K/M/D, nilai akhir, dan riwayat perhitungan."
        eyebrow="P06 · Rekap akademik"
        status={
          snapshot ? (
            <StatusBadge tone={snapshot.status === "graduated" ? "success" : "warning"}>
              {statusLabel[snapshot.status]}
            </StatusBadge>
          ) : null
        }
        title="Ujian dan nilai"
      />

      {loading ? (
        <FeedbackState
          description="Mengambil snapshot nilai terbaru."
          title="Memuat nilai"
          tone="loading"
        />
      ) : null}
      {error ? (
        <FeedbackState description={error} title="Rekap belum dapat dimuat" tone="error" />
      ) : null}

      {!loading && !snapshot ? (
        <FeedbackState
          action={
            <Button disabled={publishing} onClick={() => void publish()}>
              {publishing ? "Menghitung…" : "Buat snapshot nilai"}
            </Button>
          }
          description="Buat snapshot untuk melihat komponen yang sudah tersedia tanpa mengisi komponen kosong dengan nilai buatan."
          title="Belum ada snapshot nilai"
        />
      ) : null}

      {snapshot ? (
        <WorkSupportLayout
          support={
            <>
              <SupportPanel title="Kebijakan nilai">
                <p>Policy version {snapshot.policy_version}</p>
                <p>Bobot K/M/D: 20% / 40% / 40%</p>
              </SupportPanel>
              <SupportPanel title="Perbarui rekap">
                <p>Snapshot lama tetap tersimpan ketika perhitungan baru diterbitkan.</p>
                <Button disabled={publishing} onClick={() => void publish()} variant="secondary">
                  {publishing ? "Menghitung…" : "Terbitkan snapshot baru"}
                </Button>
              </SupportPanel>
            </>
          }
        >
          <div className={styles.componentGrid}>
            {components.map((component) => (
              <Card key={component.key}>
                <span className={styles.componentName}>{component.key.toUpperCase()}</span>
                <strong className={styles.score}>{component.value ?? "—"}</strong>
                <span>Bobot {Number(component.weight) * 100}%</span>
                <StatusBadge tone={component.status === "available" ? "success" : "warning"}>
                  {componentStatusLabel[component.status]}
                </StatusBadge>
              </Card>
            ))}
          </div>

          <Card title="Nilai akhir">
            <div className={styles.finalScore}>
              <strong>{snapshot.final_score ?? "Belum dapat dihitung"}</strong>
              <span>Dihitung {dateTimeLabel(snapshot.calculated_at)}</span>
            </div>
          </Card>

          {snapshot.missing_requirements.length ? (
            <Card title="Yang masih diperlukan">
              <ul className={styles.requirements}>
                {snapshot.missing_requirements.map((requirement) => (
                  <li key={requirement}>{missingRequirementLabel[requirement] ?? requirement}</li>
                ))}
              </ul>
            </Card>
          ) : null}

          <Card title="Riwayat snapshot">
            <DataTable
              caption="Riwayat perhitungan nilai"
              headings={["Dihitung", "Status", "K", "M", "D", "N"]}
              rows={history.map((item) => [
                dateTimeLabel(item.calculated_at),
                statusLabel[item.status],
                item.components.k.value ?? "—",
                item.components.m.value ?? "—",
                item.components.d.value ?? "—",
                item.final_score ?? "—",
              ])}
            />
          </Card>
        </WorkSupportLayout>
      ) : null}
    </AppShell>
  );
}
