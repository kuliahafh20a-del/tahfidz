export type UserRole = "participant" | "mentor" | "lecturer" | "department_admin" | "faculty_admin";

export type NavigationItem = Readonly<{
  code: string;
  href: string;
  label: string;
}>;

export const roleLabels: Record<UserRole, string> = {
  participant: "Peserta",
  mentor: "Mentor",
  lecturer: "Dosen",
  department_admin: "Admin Jurusan",
  faculty_admin: "Admin Fakultas",
};

export const roleNavigation: Record<UserRole, readonly NavigationItem[]> = {
  participant: [
    { code: "P01", href: "/peserta", label: "Beranda" },
    { code: "P02", href: "/peserta/target", label: "Target dan kalender" },
    { code: "P03", href: "/peserta/sesi/baru", label: "Ajukan sesi" },
    { code: "P04", href: "/peserta/video/baru", label: "Kirim video" },
    { code: "P05", href: "/peserta/hasil", label: "Hasil dan tindak lanjut" },
    { code: "P06", href: "/peserta/ujian", label: "Ujian dan nilai" },
  ],
  mentor: [
    { code: "M01", href: "/mentor/antrean", label: "Binaan dan antrean" },
    { code: "M02", href: "/mentor/sesi", label: "Catatan pembimbingan" },
    { code: "M03", href: "/mentor/video/kelayakan", label: "Kelayakan video" },
    { code: "M04", href: "/mentor/video/penilaian", label: "Penilaian video" },
    { code: "M05", href: "/mentor/peserta", label: "Rekap peserta" },
  ],
  lecturer: [
    { code: "D01", href: "/dosen/ujian", label: "Antrean ujian" },
    { code: "D02", href: "/dosen/ujian/paket", label: "Paket soal" },
    { code: "D03", href: "/dosen/ujian/pelaksanaan", label: "Pelaksanaan ujian" },
    { code: "D04", href: "/dosen/ujian/rekap", label: "Rekap ujian" },
  ],
  department_admin: [
    { code: "J01", href: "/department/participants", label: "Peserta dan penugasan" },
    { code: "J02", href: "/jurusan/kalender", label: "Kalender angkatan" },
    { code: "J03", href: "/jurusan/laporan", label: "Laporan jurusan" },
  ],
  faculty_admin: [{ code: "F01", href: "/fakultas/kebijakan", label: "Kebijakan dan laporan" }],
};

export function shouldShowRoleSwitcher(roles: readonly UserRole[]): boolean {
  return new Set(roles).size > 1;
}
