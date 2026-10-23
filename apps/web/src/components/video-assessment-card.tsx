"use client";

import Link from "next/link";
import { useState } from "react";

import { Button, Card, StatusBadge } from "@/components/ui";
import { apiRequest, dateTimeLabel } from "@/lib/mentoring";
import { VideoAssessment, videoOutcomeLabel } from "@/lib/video";

import styles from "./video-assessment-card.module.css";

export function VideoAssessmentCard({
  assessment,
  csrfToken,
  participant,
}: {
  assessment: VideoAssessment;
  csrfToken: string;
  participant: boolean;
}) {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const outcome = assessment.outcome ?? "not_enough";

  async function loadAudio() {
    setError(null);
    try {
      const result = await apiRequest<{ playback_url: string }>(
        participant
          ? `/me/video-assessments/${assessment.assessment_id}/audio/playback-url`
          : `/video-assessments/${assessment.assessment_id}/audio/playback-url`,
        { method: "POST", headers: { "X-CSRF-Token": csrfToken } },
      );
      setAudioUrl(result.playback_url);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Audio belum dapat diputar.");
    }
  }

  return (
    <Card className={styles.card}>
      <header>
        <div>
          <h3>
            Bagian {assessment.part_no} · {assessment.part_name}
          </h3>
          <p>
            Siklus {assessment.cycle_no} · Revisi {assessment.revision_no} ·{" "}
            {dateTimeLabel(assessment.finalized_at)}
          </p>
        </div>
        <StatusBadge tone={outcome === "enough" ? "success" : "warning"}>
          {videoOutcomeLabel[outcome]}
        </StatusBadge>
      </header>
      <dl>
        <div>
          <dt>Kesalahan terhitung</dt>
          <dd>{assessment.counted_errors}</dd>
        </div>
        <div>
          <dt>Skor manual</dt>
          <dd>{assessment.manual_score ?? "—"}</dd>
        </div>
        <div>
          <dt>Policy</dt>
          <dd>{assessment.policy_version}</dd>
        </div>
      </dl>
      {assessment.mentor_note ? <p>{assessment.mentor_note}</p> : null}
      {assessment.feedback_audio ? (
        <div className={styles.audio}>
          {audioUrl ? (
            <audio controls src={audioUrl} />
          ) : (
            <Button onClick={() => void loadAudio()} variant="secondary">
              Putar audio Mentor
            </Button>
          )}
          {error ? <small>{error}</small> : null}
        </div>
      ) : null}
      {assessment.incidents.length ? (
        <details>
          <summary>Lihat {assessment.incidents.length} kejadian</summary>
          <ul>
            {assessment.incidents.map((incident) => (
              <li key={incident.id}>
                <strong>{incident.location_text}</strong> · detik {incident.video_second} ·{" "}
                {incident.counting_reason}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
      {participant && assessment.allowed_actions.includes("create_next_revision") ? (
        <Link href="/peserta/video/baru">Kirim revisi video berikutnya</Link>
      ) : null}
    </Card>
  );
}
