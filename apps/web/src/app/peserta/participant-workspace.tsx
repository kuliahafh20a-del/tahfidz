"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AppShell, PageHeader, SupportPanel, WorkSupportLayout } from "../../components/shell";
import { Button, Card, DataTable, FeedbackState, StatusBadge } from "../../components/ui";
import {
  canRequestSession,
  targetsForPart,
  type Dashboard,
  type Target,
  type TargetStatus,
} from "../../lib/participant-calendar";
import styles from "./participant-workspace.module.css";

type ApiEnvelope<T> = { data: T };
type CursorPage<T> = { items: T[]; page: { has_more: boolean; next_cursor: string | null } };
type ApiError = { code?: string; message?: string; request_id?: string };

const statusLabels: Record<TargetStatus, string> = {
  active: "Aktif",
  scheduled: "Terjadwal",
  completed: "Selesai",
  closed: "Ditutup",
};

const statusTones = {
  active: "progress",
  scheduled: "locked",
  completed: "success",
  closed: "neutral",
} as const;

async function apiRequest<T>(path: string): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    cache: "no-store",
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as ApiError | null;
    const requestHint = error?.request_id ? ` (Request ID: ${error.request_id})` : "";
    throw new Error(`${error?.message ?? error?.code ?? "Data tidak tersedia."}${requestHint}`);
  }
  return ((await response.json()) as ApiEnvelope<T>).data;
}

function dateLabel(value: string | null): string {
  if (value === null) return "Belum tersedia";
  return new Intl.DateTimeFormat("id-ID", { dateStyle: "medium" }).format(
    new Date(`${value}T00:00:00+07:00`),
  );
}

function TargetAction({ target }: { target: Target }) {
  if (!canRequestSession(target)) {
    return (
      <span className={styles.actionUnavailable}>
        {target.locked_reason ?? "Belum ada tindakan"}
      </span>
    );
  }
  return (
    <Link className={styles.primaryLink} href={`/peserta/sesi/baru?theme_id=${target.theme.id}`}>
      Ajukan sesi
    </Link>
  );
}

function LoadingState() {
  return (
    <section aria-busy="true" aria-label="Memuat target" className={styles.skeletonGrid}>
      {[0, 1, 2].map((item) => (
        <span className={styles.skeleton} key={item} />
      ))}
    </section>
  );
}

export function ParticipantWorkspace({ view }: { view: "dashboard" | "targets" }) {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [targets, setTargets] = useState<Target[]>([]);
  const [selectedPart, setSelectedPart] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    void Promise.all([
      apiRequest<Dashboard>("/me/dashboard"),
      view === "targets"
        ? apiRequest<CursorPage<Target>>("/me/targets?limit=100").then((page) => page.items)
        : Promise.resolve([]),
    ])
      .then(([dashboardResult, targetResult]) => {
        if (!active) return;
        setDashboard(dashboardResult);
        setTargets(targetResult);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Data tidak tersedia.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reloadKey, view]);

  const visibleTargets = useMemo(
    () => targetsForPart(targets, selectedPart),
    [selectedPart, targets],
  );
  const accountName = dashboard?.participant.display_name ?? "Peserta";
  const cohortName = dashboard?.participant.cohort_name ?? "Program Tahfidz";

  function retry(): void {
    setLoading(true);
    setError(null);
    setReloadKey((key) => key + 1);
  }

  return (
    <AppShell accountName={accountName} initialRole="participant" organization={cohortName}>
      <PageHeader
        breadcrumbs={
          view === "dashboard"
            ? [{ label: "Beranda" }]
            : [{ href: "/peserta", label: "Beranda" }, { label: "Target dan kalender" }]
        }
        description={
          view === "dashboard"
            ? "Lihat target terdekat, bagian aktif, dan langkah berikutnya."
            : "Ikuti 40 tema Juz 30 dalam lima bagian berdasarkan tenggat efektif."
        }
        eyebrow={view === "dashboard" ? "P01 · Peserta" : "P02 · Peserta"}
        status={
          dashboard ? (
            <StatusBadge tone="progress">
              {dashboard.progress.active_part?.name ?? "Program selesai"}
            </StatusBadge>
          ) : undefined
        }
        title={view === "dashboard" ? "Beranda peserta" : "Target dan kalender"}
      />

      {loading ? <LoadingState /> : null}
      {!loading && error ? (
        <FeedbackState
          action={<Button onClick={retry}>Coba lagi</Button>}
          description={error}
          title="Target belum dapat dimuat"
          tone="error"
        />
      ) : null}
      {!loading && !error && dashboard === null ? (
        <FeedbackState
          description="Belum ada kepesertaan aktif. Hubungi Admin Jurusan untuk bergabung ke angkatan."
          title="Belum ada target"
        />
      ) : null}

      {!loading && !error && dashboard ? (
        view === "dashboard" ? (
          <DashboardView dashboard={dashboard} />
        ) : (
          <TargetsView
            dashboard={dashboard}
            onSelectPart={setSelectedPart}
            selectedPart={selectedPart}
            targets={visibleTargets}
          />
        )
      ) : null}
    </AppShell>
  );
}

function DashboardView({ dashboard }: { dashboard: Dashboard }) {
  const { progress } = dashboard;
  return (
    <WorkSupportLayout
      support={
        <SupportPanel title="Cara membaca progres">
          <p>Tanggal yang tampil adalah tenggat efektif setelah perubahan kalender yang sah.</p>
          <ul>
            <li>Target aktif dapat diajukan dalam sesi.</li>
            <li>Bagian berikutnya terbuka setelah bagian aktif selesai.</li>
            <li>Target yang belum jatuh tempo tidak diberi nilai buatan.</li>
          </ul>
        </SupportPanel>
      }
    >
      <section aria-label="Ringkasan progres" className={styles.metrics}>
        <Card>
          <span>Progres tema</span>
          <strong>
            {progress.completed_targets}/{progress.total_targets}
          </strong>
          <small>{progress.completion_percentage}% selesai</small>
        </Card>
        <Card>
          <span>Target tertunggak</span>
          <strong>{progress.overdue_targets}</strong>
          <small>{progress.on_track ? "Progres sesuai jadwal" : "Perlu tindak lanjut"}</small>
        </Card>
        <Card>
          <span>Proyeksi selesai</span>
          <strong className={styles.dateMetric}>
            {dateLabel(progress.projected_completion_date)}
          </strong>
          <small>Berdasarkan tenggat efektif</small>
        </Card>
      </section>

      {dashboard.next_target ? (
        <Card className={styles.nextTarget} title="Pekerjaan berikutnya">
          <div>
            <span className={styles.targetCode}>{dashboard.next_target.theme.code}</span>
            <h3>{dashboard.next_target.theme.name}</h3>
            <p>
              {dashboard.next_target.theme.part_name} · Tenggat{" "}
              {dateLabel(dashboard.next_target.effective_due_date)}
            </p>
          </div>
          <TargetAction target={dashboard.next_target} />
        </Card>
      ) : (
        <FeedbackState
          description="Semua target aktif telah selesai atau belum ada tindakan yang tersedia."
          title="Tidak ada pekerjaan mendesak"
        />
      )}

      {dashboard.upcoming_targets.length ? (
        <DataTable
          caption="Target terdekat"
          headings={["Target", "Status", "Tenggat efektif", "Berikutnya"]}
          rows={dashboard.upcoming_targets.map((target) => [
            `${target.theme.code} · ${target.theme.name}`,
            <StatusBadge key={`${target.id}-status`} tone={statusTones[target.status]}>
              {statusLabels[target.status]}
            </StatusBadge>,
            dateLabel(target.effective_due_date),
            <TargetAction key={`${target.id}-action`} target={target} />,
          ])}
        />
      ) : (
        <FeedbackState
          description="Target akan muncul setelah kalender angkatan dibuat."
          title="Kalender masih kosong"
        />
      )}
      <Link className={styles.secondaryLink} href="/peserta/target">
        Lihat seluruh 40 tema
      </Link>
    </WorkSupportLayout>
  );
}

function TargetsView({
  dashboard,
  onSelectPart,
  selectedPart,
  targets,
}: {
  dashboard: Dashboard;
  onSelectPart: (partId: string | null) => void;
  selectedPart: string | null;
  targets: Target[];
}) {
  return (
    <WorkSupportLayout
      support={
        <SupportPanel title="Kalender angkatan">
          <p>Mulai {dateLabel(dashboard.participant.cohort_start_date)}</p>
          <p>Proyeksi selesai {dateLabel(dashboard.progress.projected_completion_date)}</p>
          <p>
            {dashboard.progress.completed_targets} dari {dashboard.progress.total_targets} tema
            selesai.
          </p>
        </SupportPanel>
      }
    >
      <div className={styles.partFilters} aria-label="Filter bagian">
        <button
          aria-pressed={selectedPart === null}
          onClick={() => onSelectPart(null)}
          type="button"
        >
          Semua bagian
        </button>
        {dashboard.progress.parts.map((part) => (
          <button
            aria-pressed={selectedPart === part.id}
            key={part.id}
            onClick={() => onSelectPart(part.id)}
            type="button"
          >
            <span>{part.name}</span>
            <small>
              {part.completed_targets}/{part.total_targets} ·{" "}
              {part.status === "locked"
                ? "Terkunci"
                : part.status === "active"
                  ? "Aktif"
                  : "Selesai"}
            </small>
          </button>
        ))}
      </div>

      {dashboard.progress.parts
        .filter(
          (part) => part.status === "locked" && (selectedPart === null || selectedPart === part.id),
        )
        .map((part) => (
          <FeedbackState
            description={
              part.locked_reason ?? "Selesaikan bagian sebelumnya untuk membuka bagian ini."
            }
            key={part.id}
            title={`${part.name} terkunci`}
            tone="locked"
          />
        ))}

      {targets.length ? (
        <DataTable
          caption={`${targets.length} target ditampilkan`}
          headings={[
            "Tema",
            "Bagian",
            "Tenggat awal",
            "Tenggat efektif",
            "Status",
            "Hasil / Nilai Keaktifan",
            "Tindakan",
          ]}
          rows={targets.map((target) => [
            `${target.theme.code} · ${target.theme.name}`,
            target.theme.part_name,
            dateLabel(target.initial_due_date),
            dateLabel(target.effective_due_date),
            <StatusBadge key={`${target.id}-status`} tone={statusTones[target.status]}>
              {statusLabels[target.status]}
            </StatusBadge>,
            target.activity_score === null ? "Belum dinilai" : target.activity_score,
            <TargetAction key={`${target.id}-action`} target={target} />,
          ])}
        />
      ) : (
        <FeedbackState
          description="Tidak ada target pada filter ini. Pilih bagian lain atau tampilkan semua bagian."
          title="Target tidak ditemukan"
        />
      )}
    </WorkSupportLayout>
  );
}
