"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { AppShell, PageHeader, SupportPanel, WorkSupportLayout } from "@/components/shell";
import { Button, Card, FeedbackState, StatusBadge } from "@/components/ui";
import { apiRequest, SessionContext } from "@/lib/mentoring";
import { EligibilityDecision, VideoEligibility } from "@/lib/video";

import styles from "./workspace.module.css";

const decisionLabel: Record<EligibilityDecision, string> = {
  eligible: "Layak",
  ineligible: "Tidak layak",
};

export function VideoEligibilityWorkspace() {
  const [context, setContext] = useState<SessionContext | null>(null);
  const [items, setItems] = useState<VideoEligibility[]>([]);
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
    ])
      .then(([loadedContext, loadedItems]) => {
        if (!active) return;
        setContext(loadedContext);
        setItems(loadedItems);
        setSelectedId((current) => current ?? loadedItems[0]?.video_version_id ?? null);
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
    () => items.find((item) => item.video_version_id === selectedId) ?? null,
    [items, selectedId],
  );
  const pendingCount = items.filter((item) => item.review?.status !== "final").length;

  function updateItem(updated: VideoEligibility, message: string): void {
    setItems((current) =>
      current.map((item) => (item.video_version_id === updated.video_version_id ? updated : item)),
    );
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
        breadcrumbs={[{ href: "/mentor/antrean", label: "Antrean" }, { label: "Kelayakan video" }]}
        description="Periksa mutu teknis rekaman tanpa memberikan hasil akademik."
        eyebrow="M03 · Pemeriksaan teknis"
        status={<StatusBadge tone="warning">{pendingCount} menunggu</StatusBadge>}
        title="Kelayakan video"
      />

      {loading ? (
        <FeedbackState
          description="Mengambil video peserta binaan aktif."
          title="Memuat antrean"
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
          title="Kelayakan belum dapat diproses"
          tone="error"
        />
      ) : null}
      {notice ? <FeedbackState description={notice} title="Perubahan tersimpan" /> : null}

      {!loading && !error ? (
        <WorkSupportLayout
          support={
            <>
              <SupportPanel title="Batas keputusan">
                <p className={styles.supportCopy}>
                  Layak hanya membuka tahap penilaian video. Keputusan ini tidak memberi skor atau
                  hasil akademik.
                </p>
              </SupportPanel>
              <SupportPanel title="Aturan Tidak Layak">
                <p className={styles.supportCopy}>
                  Tandai minimal satu butir gagal dan tuliskan alasan yang dapat ditindaklanjuti
                  peserta.
                </p>
              </SupportPanel>
            </>
          }
        >
          <Card title={`Antrean video (${items.length})`}>
            {items.length === 0 ? (
              <FeedbackState
                description="Belum ada video dari peserta binaan aktif."
                title="Antrean kosong"
              />
            ) : (
              <div className={styles.queue}>
                {items.map((item) => (
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
                        {item.participant.nim} · Bagian {item.part_no} · Versi{" "}
                        {item.video_version_no}
                      </small>
                    </span>
                    <StatusBadge tone={item.review?.status === "final" ? "success" : "warning"}>
                      {item.review?.status === "final"
                        ? item.review.decision
                          ? decisionLabel[item.review.decision]
                          : "Final"
                        : item.review
                          ? "Draft"
                          : "Baru"}
                    </StatusBadge>
                  </button>
                ))}
              </div>
            )}
          </Card>

          {selected && context ? (
            <EligibilityEditor
              item={selected}
              key={`${selected.video_version_id}-${selected.review?.row_version ?? 0}`}
              onError={setError}
              onUpdated={updateItem}
              session={context}
            />
          ) : null}
        </WorkSupportLayout>
      ) : null}
    </AppShell>
  );
}

function EligibilityEditor({
  item,
  onError,
  onUpdated,
  session,
}: {
  item: VideoEligibility;
  onError: (message: string | null) => void;
  onUpdated: (item: VideoEligibility, message: string) => void;
  session: SessionContext;
}) {
  const existing = new Map(item.review?.checks.map((check) => [check.code, check]));
  const [busy, setBusy] = useState(false);
  const isFinal = item.review?.status === "final";

  function payload(form: HTMLFormElement) {
    const values = new FormData(form);
    return {
      checklist_version: item.checklist_version,
      decision: values.get("decision"),
      reason: values.get("reason") || null,
      checks: item.criteria.map((criterion) => ({
        code: criterion.code,
        passed: values.get(`passed-${criterion.code}`) === "on",
        note: values.get(`note-${criterion.code}`) || null,
      })),
      expected_version: item.review?.row_version ?? null,
    };
  }

  async function save(form: HTMLFormElement, finalize: boolean): Promise<void> {
    setBusy(true);
    onError(null);
    try {
      const body = payload(form);
      const updated = await apiRequest<VideoEligibility>(
        `/video-versions/${item.video_version_id}/${finalize ? "eligibility" : "eligibility-draft"}`,
        {
          method: finalize ? "POST" : "PUT",
          headers: {
            "Idempotency-Key": crypto.randomUUID(),
            "X-CSRF-Token": session.csrf_token,
          },
          body: JSON.stringify(body),
        },
      );
      onUpdated(
        updated,
        finalize
          ? `Keputusan ${updated.review?.decision === "eligible" ? "Layak" : "Tidak Layak"} telah difinalisasi.`
          : "Draft checklist kelayakan tersimpan.",
      );
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Review gagal disimpan.");
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
        <fieldset disabled={busy || isFinal}>
          <legend>Checklist {item.checklist_version}</legend>
          {item.criteria.map((criterion) => (
            <div className={styles.criterion} key={criterion.code}>
              <label className={styles.checkLabel}>
                <input
                  defaultChecked={existing.get(criterion.code)?.passed ?? false}
                  name={`passed-${criterion.code}`}
                  type="checkbox"
                />
                <span>{criterion.label}</span>
              </label>
              <label>
                Catatan
                <input
                  defaultValue={existing.get(criterion.code)?.note ?? ""}
                  name={`note-${criterion.code}`}
                  placeholder="Opsional"
                />
              </label>
            </div>
          ))}
        </fieldset>
        <label>
          Keputusan
          <select
            defaultValue={item.review?.decision ?? "eligible"}
            disabled={isFinal}
            name="decision"
          >
            <option value="eligible">Layak</option>
            <option value="ineligible">Tidak layak</option>
          </select>
        </label>
        <label>
          Alasan
          <textarea
            defaultValue={item.review?.reason ?? ""}
            disabled={isFinal}
            name="reason"
            placeholder="Wajib untuk keputusan Tidak Layak"
            rows={3}
          />
        </label>
        {isFinal ? (
          <FeedbackState
            description="Keputusan final tidak dapat diedit. Gunakan versi media pengganti untuk pemeriksaan baru."
            title="Review telah final"
          />
        ) : (
          <div className={styles.actions}>
            <Button disabled={busy} type="submit" variant="secondary">
              Simpan draft
            </Button>
            <Button
              disabled={busy || !item.review}
              onClick={(event) => {
                const form = event.currentTarget.form;
                if (form) void save(form, true);
              }}
              type="button"
            >
              Finalisasi kelayakan
            </Button>
          </div>
        )}
      </form>
    </Card>
  );
}
