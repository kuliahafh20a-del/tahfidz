"""Seed reproducible lecturer exam simulation data.

Revision ID: 20261024_0020
Revises: 20261024_0019
Create Date: 2026-10-24 20:30:00+07:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261024_0020"
down_revision: str | None = "20261024_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Prepare four participants across the lecturer exam workflow."""
    op.execute(
        """
        CREATE TEMP TABLE demo_exam_participants ON COMMIT DROP AS
        SELECT enrollment.id AS enrollment_id,
               enrollment.nim_snapshot,
               cohort.policy_version_id,
               cohort.curriculum_version_id,
               lecturer.id AS lecturer_id,
               greatest(now() - interval '1 minute', role_grant.valid_from) AS assignment_start,
               sample.exam_status,
               sample.days_offset
          FROM (VALUES
                ('1247010065', 'draft', 3),
                ('1247010059', 'scheduled', 2),
                ('1247010078', 'in_progress', 0),
                ('1247010083', 'final', -2)
               ) AS sample(nim, exam_status, days_offset)
          JOIN app.enrollments AS enrollment ON enrollment.nim_snapshot = sample.nim
          JOIN app.cohorts AS cohort ON cohort.id = enrollment.cohort_id
          CROSS JOIN (
              SELECT id FROM app.users
               WHERE login_identifier = '197105172007012022'
          ) AS lecturer
          JOIN app.role_grants AS role_grant
            ON role_grant.user_id = lecturer.id
           AND role_grant.organization_id = cohort.organization_id
           AND role_grant.role = 'lecturer'
           AND role_grant.valid_from <= now()
           AND (role_grant.valid_to IS NULL OR role_grant.valid_to > now());

        INSERT INTO app.assignments
            (enrollment_id, staff_id, role, valid_from, reason)
        SELECT participant.enrollment_id,
               participant.lecturer_id,
               'lecturer',
               participant.assignment_start,
               'Data simulasi alur ujian Dosen'
          FROM demo_exam_participants AS participant
         WHERE NOT EXISTS (
             SELECT 1 FROM app.assignments AS assignment
              WHERE assignment.enrollment_id = participant.enrollment_id
                AND assignment.role = 'lecturer'
                AND assignment.valid_to IS NULL
         );

        CREATE TEMP TABLE demo_exam_videos ON COMMIT DROP AS
        SELECT gen_random_uuid() AS attempt_id,
               gen_random_uuid() AS version_id,
               gen_random_uuid() AS review_id,
               gen_random_uuid() AS assessment_id,
               participant.enrollment_id,
               participant.policy_version_id,
               participant.lecturer_id,
               part.id AS part_id,
               part.sequence_no
          FROM demo_exam_participants AS participant
          JOIN app.parts AS part
            ON part.curriculum_version_id = participant.curriculum_version_id;

        INSERT INTO app.video_attempts
            (id, enrollment_id, part_id, cycle_no, revision_no, status)
        SELECT attempt_id, enrollment_id, part_id, 1, 0, 'finalized'
          FROM demo_exam_videos;

        INSERT INTO app.video_versions
            (id, attempt_id, version_no, video_url, recorded_date, submitted_at, status)
        SELECT version_id,
               attempt_id,
               1,
               'https://example.invalid/simulasi-ujian/' || enrollment_id || '/' || sequence_no,
               current_date - (10 - sequence_no),
               now() - ((10 - sequence_no) * interval '1 day'),
               'available'
          FROM demo_exam_videos;

        INSERT INTO app.eligibility_reviews
            (id, video_version_id, reviewer_id, checklist_version, decision, status, finalized_at)
        SELECT review_id, version_id, lecturer_id, 'simulation-v1',
               'eligible', 'final', now() - interval '4 days'
          FROM demo_exam_videos;

        INSERT INTO app.assessment_records
            (id, enrollment_id, assessor_id, policy_version_id, kind, actual_at,
             manual_score, status, finalized_at)
        SELECT assessment_id, enrollment_id, lecturer_id, policy_version_id, 'video',
               now() - interval '4 days', 8, 'final', now() - interval '4 days'
          FROM demo_exam_videos;

        INSERT INTO app.video_assessments
            (id, video_version_id, eligibility_review_id, counted_errors, outcome, notes)
        SELECT assessment_id, version_id, review_id, 1, 'enough',
               'Simulasi: video bagian dinyatakan Cukup.'
          FROM demo_exam_videos;

        INSERT INTO app.question_versions
            (id, question_key, author_id, source, kind, stimulus,
             answer_reference, scope, version_no, status)
        VALUES
            ('02000000-0000-4000-8000-000000000001',
             '02000000-0000-4000-8000-000000000011', NULL, 'application',
             'continue_verses', 'Lanjutkan bacaan Surah An-Nas dari ayat yang ditentukan Dosen.',
             jsonb_build_object('guidance', 'Nilai kelancaran dan ketepatan lanjutan ayat.'),
             jsonb_build_object('surah', 'An-Nas', 'surah_no', 114), 1, 'verified'),
            ('02000000-0000-4000-8000-000000000002',
             '02000000-0000-4000-8000-000000000012', NULL, 'application',
             'surah_order', 'Sebutkan urutan tiga surah terakhir dalam Al-Quran.',
             jsonb_build_object('answer', jsonb_build_array('Al-Ikhlas','Al-Falaq','An-Nas')),
             jsonb_build_object('juz', 30), 1, 'verified'),
            ('02000000-0000-4000-8000-000000000003',
             '02000000-0000-4000-8000-000000000013', NULL, 'application',
             'recitation', 'Bacakan Surah Al-Ikhlas secara lengkap.',
             jsonb_build_object('guidance', 'Nilai hafalan, tajwid, dan kelancaran.'),
             jsonb_build_object('surah', 'Al-Ikhlas', 'surah_no', 112), 1, 'verified');

        CREATE TEMP TABLE demo_exams ON COMMIT DROP AS
        SELECT gen_random_uuid() AS exam_id,
               participant.*
          FROM demo_exam_participants AS participant;

        INSERT INTO app.exams
            (id, enrollment_id, lecturer_id, policy_version_id, scheduled_at,
             actual_at, notes, status, row_version, finalized_at, d_score,
             evidence_media_ids)
        SELECT exam_id,
               enrollment_id,
               lecturer_id,
               policy_version_id,
               date_trunc('day', now()) + (days_offset * interval '1 day') + interval '09:00',
               CASE WHEN exam_status IN ('in_progress', 'final')
                    THEN now() - interval '2 hours' END,
               'Data simulasi untuk pengecekan halaman Dosen.',
               exam_status,
               1,
               CASE WHEN exam_status = 'final' THEN now() - interval '1 day' END,
               CASE WHEN exam_status = 'final' THEN 8.000 END,
               '[]'::jsonb
          FROM demo_exams;

        CREATE TEMP TABLE demo_exam_items ON COMMIT DROP AS
        SELECT gen_random_uuid() AS item_id,
               exam.exam_id,
               question.id AS question_id,
               row_number() OVER (
                   PARTITION BY exam.exam_id ORDER BY question.id
               )::integer AS sequence_no,
               question.source,
               question.kind,
               question.stimulus,
               question.scope,
               question.answer_reference,
               question.question_key,
               question.version_no,
               exam.enrollment_id,
               exam.lecturer_id,
               exam.policy_version_id,
               exam.exam_status
          FROM demo_exams AS exam
          JOIN app.question_versions AS question
            ON question.id IN (
                '02000000-0000-4000-8000-000000000001',
                '02000000-0000-4000-8000-000000000002',
                '02000000-0000-4000-8000-000000000003'
            );

        INSERT INTO app.exam_items
            (id, exam_id, question_version_id, sequence_no, question_snapshot, weight)
        SELECT item_id,
               exam_id,
               question_id,
               sequence_no,
               jsonb_build_object(
                   'source', source,
                   'kind', kind,
                   'stimulus', stimulus,
                   'scope', scope,
                   'answer_reference', answer_reference,
                   'question_key', question_key::text,
                   'version_no', version_no
               ),
               NULL
          FROM demo_exam_items;

        CREATE TEMP TABLE demo_exam_scores ON COMMIT DROP AS
        SELECT gen_random_uuid() AS assessment_id, item.*
          FROM demo_exam_items AS item
         WHERE item.exam_status IN ('in_progress', 'final');

        INSERT INTO app.assessment_records
            (id, enrollment_id, assessor_id, policy_version_id, kind, actual_at,
             manual_score, status, finalized_at)
        SELECT assessment_id,
               enrollment_id,
               lecturer_id,
               policy_version_id,
               'exam',
               now() - interval '2 hours',
               CASE WHEN exam_status = 'final' THEN 8 ELSE NULL END,
               CASE WHEN exam_status = 'final' THEN 'final' ELSE 'draft' END,
               CASE WHEN exam_status = 'final' THEN now() - interval '1 day' END
          FROM demo_exam_scores;

        INSERT INTO app.exam_assessments (id, exam_item_id, notes)
        SELECT assessment_id,
               item_id,
               CASE WHEN exam_status = 'final'
                    THEN 'Simulasi penilaian ujian selesai.'
                    ELSE 'Draft penilaian sedang berlangsung.' END
          FROM demo_exam_scores;
        """
    )


def downgrade() -> None:
    """Remove only records identified as exam simulation data."""
    op.execute(
        """
        DELETE FROM app.exam_assessments
         WHERE exam_item_id IN (
             SELECT id FROM app.exam_items
              WHERE exam_id IN (
                  SELECT id FROM app.exams
                   WHERE notes = 'Data simulasi untuk pengecekan halaman Dosen.'
              )
         );
        DELETE FROM app.assessment_records
         WHERE kind = 'exam'
           AND id NOT IN (SELECT id FROM app.exam_assessments)
           AND enrollment_id IN (
               SELECT id FROM app.enrollments
                WHERE nim_snapshot IN ('1247010065','1247010059','1247010078','1247010083')
           );
        DELETE FROM app.exams
         WHERE notes = 'Data simulasi untuk pengecekan halaman Dosen.';
        DELETE FROM app.video_assessments
         WHERE notes = 'Simulasi: video bagian dinyatakan Cukup.';
        DELETE FROM app.assessment_records
         WHERE kind = 'video'
           AND enrollment_id IN (
               SELECT id FROM app.enrollments
                WHERE nim_snapshot IN ('1247010065','1247010059','1247010078','1247010083')
           );
        DELETE FROM app.eligibility_reviews WHERE checklist_version = 'simulation-v1';
        DELETE FROM app.video_versions
         WHERE video_url LIKE 'https://example.invalid/simulasi-ujian/%';
        DELETE FROM app.video_attempts
         WHERE enrollment_id IN (
             SELECT id FROM app.enrollments
              WHERE nim_snapshot IN ('1247010065','1247010059','1247010078','1247010083')
         ) AND status = 'finalized';
        DELETE FROM app.assignments
         WHERE reason = 'Data simulasi alur ujian Dosen';
        DELETE FROM app.question_versions
         WHERE id IN (
             '02000000-0000-4000-8000-000000000001',
             '02000000-0000-4000-8000-000000000002',
             '02000000-0000-4000-8000-000000000003'
         );
        """
    )
