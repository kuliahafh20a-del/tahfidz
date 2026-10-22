"use client";

import { useState } from "react";

import { AppShell, PageHeader, SupportPanel, WorkSupportLayout } from "@/components/shell";
import {
  Button,
  Card,
  ConfirmationDialog,
  DataTable,
  FeedbackState,
  FormField,
  StatusBadge,
} from "@/components/ui";

import styles from "./dashboard.module.css";

const targetRows = [
  [
    "Tema 01 · An-Naba",
    <StatusBadge key="status-1" tone="success">
      Cukup
    </StatusBadge>,
    "Tema 02",
  ],
  [
    "Tema 02 · An-Nazi'at",
    <StatusBadge key="status-2" tone="progress">
      Dalam proses
    </StatusBadge>,
    "Lanjutkan sesi",
  ],
  [
    "Tema 03 · 'Abasa",
    <StatusBadge key="status-3" tone="locked">
      Terkunci
    </StatusBadge>,
    "Selesaikan Tema 02",
  ],
] as const;

export function DashboardShowcase() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [message, setMessage] = useState("Komponen app shell siap digunakan.");

  return (
    <AppShell
      accountName="Ahmad Fikri"
      availableRoles={["participant", "mentor", "lecturer", "department_admin", "faculty_admin"]}
      initialRole="participant"
      organization="Fakultas Ilmu Keislaman"
    >
      <PageHeader
        breadcrumbs={[{ href: "/", label: "Peserta" }, { label: "Beranda" }]}
        description="Pantau target, jadwal pendampingan, dan pekerjaan berikutnya dalam satu ruang yang jelas."
        eyebrow="P01 · Ruang kerja peserta"
        status={<StatusBadge tone="progress">Bagian 1 aktif</StatusBadge>}
        title="Selamat datang, Ahmad"
      />

      <WorkSupportLayout
        support={
          <SupportPanel title="Informasi pendamping">
            <p>Fokuskan pekerjaan pada tema aktif sebelum membuka bagian berikutnya.</p>
            <ul>
              <li>Target pekan ini: Tema 02</li>
              <li>Tenggat: 29 Oktober 2026</li>
              <li>Mentor: Ustadzah Hana</li>
            </ul>
          </SupportPanel>
        }
      >
        <section aria-label="Ringkasan progres" className={styles.metrics}>
          <Card>
            <span className={styles.metricLabel}>Tema cukup</span>
            <strong className={styles.metricValue}>8 dari 44</strong>
            <span className={styles.metricMeta}>Bagian 1 · periode aktif</span>
          </Card>
          <Card>
            <span className={styles.metricLabel}>Sesi berikutnya</span>
            <strong className={styles.metricValue}>24 Okt</strong>
            <span className={styles.metricMeta}>10.00 WIB · video call</span>
          </Card>
        </section>

        <Card title="Pekerjaan terdekat">
          <DataTable
            caption="Target hafalan aktif"
            headings={["Target", "Status", "Berikutnya"]}
            rows={targetRows}
          />
        </Card>

        <Card title="Catatan untuk sesi berikutnya">
          <div className={styles.formExample}>
            <FormField
              help="Catatan ini tersimpan sebagai draft dan dapat diubah sebelum diajukan."
              label="Fokus latihan"
              name="practice-focus"
              placeholder="Contoh: perbaiki makhraj ayat 12"
            />
            <div className={styles.actions}>
              <Button type="button" variant="secondary">
                Simpan draft
              </Button>
              <Button onClick={() => setDialogOpen(true)} type="button">
                Tinjau pengajuan sesi
              </Button>
            </div>
          </div>
        </Card>

        <FeedbackState
          description="Perubahan status, hasil request, dan kegagalan diumumkan secara aksesibel."
          title={message}
        />
      </WorkSupportLayout>

      <ConfirmationDialog
        confirmLabel="Ajukan sesi"
        onConfirm={() => setMessage("Pengajuan sesi berhasil dikirim.")}
        onOpenChange={setDialogOpen}
        open={dialogOpen}
        title="Ajukan sesi untuk Tema 02"
      >
        <p>
          Pastikan tema, metode, dan waktu usulan sudah benar. Pengajuan akan dikirim kepada Mentor
          aktif untuk ditinjau.
        </p>
      </ConfirmationDialog>
    </AppShell>
  );
}
