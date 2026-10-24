import type { Metadata } from "next";
import Link from "next/link";

import styles from "./landing.module.css";

export const metadata: Metadata = {
  description:
    "YAQin mendampingi perjalanan hafalan Juz 30 melalui target yang jelas, pembimbingan terarah, dan penilaian yang dapat ditelusuri.",
  title: "Pendampingan Hafalan Juz 30",
};

const ArrowIcon = () => (
  <svg aria-hidden="true" viewBox="0 0 20 20">
    <path d="M4 10h11M11 5l5 5-5 5" />
  </svg>
);

const CheckIcon = () => (
  <svg aria-hidden="true" viewBox="0 0 20 20">
    <path d="m4 10 4 4 8-9" />
  </svg>
);

export default function HomePage() {
  return (
    <main className={styles.page}>
      <a className={styles.skipLink} href="#konten-utama">
        Lewati ke konten utama
      </a>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link aria-label="YAQin - beranda" className={styles.brand} href="/">
            <span className={styles.brandMark}>YQ</span>
            <span>
              <strong>YAQin</strong>
              <small>Yakin · Amalin · Mutqin</small>
            </span>
          </Link>
          <nav aria-label="Navigasi utama" className={styles.nav}>
            <a href="#perjalanan">Perjalanan</a>
            <a href="#fitur">Fitur</a>
            <a href="#peran">Untuk siapa</a>
          </nav>
          <Link className={styles.headerCta} href="/login">
            Masuk <ArrowIcon />
          </Link>
        </div>
      </header>

      <section className={styles.hero} id="konten-utama">
        <div className={styles.heroGlow} />
        <div className={styles.heroInner}>
          <div className={styles.heroCopy}>
            <p className={styles.eyebrow}>
              <span /> Pendampingan hafalan Juz 30
            </p>
            <h1>
              Bertumbuh dalam hafalan, <em>terarah</em> dalam perjalanan.
            </h1>
            <p className={styles.heroLead}>
              YAQin menyatukan peserta, mentor, dosen, dan pengelola dalam satu ruang pendampingan
              yang jelas—dari tema pertama hingga kelulusan.
            </p>
            <div className={styles.heroActions}>
              <Link className={styles.primaryCta} href="/login">
                Masuk ke YAQin <ArrowIcon />
              </Link>
              <a className={styles.secondaryCta} href="#perjalanan">
                Lihat cara kerjanya
              </a>
            </div>
            <div className={styles.trustLine}>
              <span>
                <CheckIcon /> Target yang jelas
              </span>
              <span>
                <CheckIcon /> Progres yang dapat ditelusuri
              </span>
            </div>
          </div>

          <div aria-label="Gambaran progres peserta" className={styles.heroVisual}>
            <div className={styles.orbitOne} />
            <div className={styles.orbitTwo} />
            <div className={styles.progressCard}>
              <div className={styles.cardTopline}>
                <div>
                  <span className={styles.cardEyebrow}>Perjalanan hafalan</span>
                  <strong>Juz 30</strong>
                </div>
                <span className={styles.activeBadge}>Aktif</span>
              </div>
              <div className={styles.progressRing}>
                <div>
                  <strong>8</strong>
                  <span>dari 40 tema</span>
                </div>
              </div>
              <div className={styles.currentStep}>
                <span className={styles.stepNumber}>02</span>
                <div>
                  <small>Sedang dipelajari</small>
                  <strong>An-Nazi&apos;at</strong>
                </div>
                <span className={styles.stepStatus}>Berproses</span>
              </div>
              <div className={styles.cardFooter}>
                <div>
                  <span>Bagian aktif</span>
                  <strong>Bagian 1</strong>
                </div>
                <div>
                  <span>Berikutnya</span>
                  <strong>Sesi mentor</strong>
                </div>
              </div>
            </div>
            <div className={styles.floatingNote}>
              <span className={styles.noteIcon}>
                <CheckIcon />
              </span>
              <div>
                <small>Tema 01</small>
                <strong>Hasil cukup</strong>
              </div>
            </div>
            <div className={styles.floatingVerse} aria-hidden="true">
              <span>اقْرَأْ وَارْتَقِ</span>
              <small>Baca dan naiklah</small>
            </div>
          </div>
        </div>
      </section>

      <section aria-label="Peran pengguna YAQin" className={styles.roleStrip}>
        <div className={styles.roleStripInner}>
          <p>Satu perjalanan, didampingi bersama</p>
          <div>
            <span>Peserta</span><i /><span>Mentor</span><i /><span>Dosen</span><i />
            <span>Jurusan</span><i /><span>Fakultas</span>
          </div>
        </div>
      </section>

      <section className={styles.journey} id="perjalanan">
        <div className={styles.sectionIntro}>
          <p className={styles.eyebrow}>Alur yang utuh</p>
          <h2>Dari niat baik menjadi progres yang nyata.</h2>
          <p>
            Setiap tahap memiliki tujuan, bukti, dan tindak lanjut yang jelas—tanpa menghilangkan
            sisi manusiawi dalam proses belajar.
          </p>
        </div>
        <div className={styles.journeyGrid}>
          <article>
            <span className={styles.journeyNumber}>01</span><div className={styles.journeyLine} />
            <h3>Temukan arah</h3>
            <p>Lihat 40 tema Juz 30, bagian aktif, tenggat, dan pekerjaan terdekat.</p>
            <span className={styles.journeyTag}>Target & kalender</span>
          </article>
          <article>
            <span className={styles.journeyNumber}>02</span><div className={styles.journeyLine} />
            <h3>Tumbuh bersama</h3>
            <p>Ajukan sesi, terima catatan, dan lanjutkan perbaikan bersama Mentor.</p>
            <span className={styles.journeyTag}>Sesi & video</span>
          </article>
          <article>
            <span className={styles.journeyNumber}>03</span><div className={styles.journeyLine} />
            <h3>Tuntaskan dengan yakin</h3>
            <p>Ikuti ujian dan pahami nilai beserta sumber perhitungannya.</p>
            <span className={styles.journeyTag}>Ujian & nilai</span>
          </article>
        </div>
      </section>

      <section className={styles.features} id="fitur">
        <div className={styles.featuresInner}>
          <div className={styles.sectionIntroLight}>
            <p className={styles.eyebrow}>Dirancang untuk kejelasan</p>
            <h2>Satu sumber informasi untuk setiap keputusan.</h2>
          </div>
          <div className={styles.featureGrid}>
            <article className={styles.featurePrimary}>
              <div className={styles.featureIcon}>40</div>
              <div>
                <h3>Kurikulum yang terstruktur</h3>
                <p>Empat puluh empat tema tersusun dalam lima bagian, dengan prasyarat yang terlihat sebelum peserta melanjutkan.</p>
              </div>
              <div className={styles.miniPath} aria-hidden="true">
                <span className={styles.pathDone}>1</span><i /><span className={styles.pathActive}>2</span><i />
                <span>3</span><i /><span>4</span><i /><span>5</span>
              </div>
            </article>
            <article>
              <div className={styles.lineIcon} aria-hidden="true"><span /><span /><span /></div>
              <h3>Pendampingan yang berkelanjutan</h3>
              <p>Catatan sesi, video, dan audio membantu peserta memahami langkah perbaikan.</p>
            </article>
            <article>
              <div className={styles.shieldIcon} aria-hidden="true"><CheckIcon /></div>
              <h3>Hak akses yang terjaga</h3>
              <p>Setiap peran hanya melihat informasi dan tindakan sesuai tanggung jawabnya.</p>
            </article>
            <article className={styles.featureWide}>
              <div>
                <span className={styles.featureKicker}>Nilai tanpa tebakan</span>
                <h3>Transparan dari sumber hingga hasil.</h3>
                <p>Komponen yang belum tersedia tetap kosong. Riwayat penilaian dan versi kebijakan dipertahankan agar hasil dapat ditelusuri.</p>
              </div>
              <div className={styles.gradePreview} aria-label="Contoh komponen nilai">
                <div><span>20%</span><strong>Nilai Keaktifan</strong><small>Terhitung</small></div>
                <div><span>50%</span><strong>Nilai Proses Hafalan (Mentor)</strong><small>Terhitung</small></div>
                <div className={styles.gradePending}><span>30%</span><strong>Nilai Ujian (Dosen)</strong><small>Menunggu ujian</small></div>
              </div>
            </article>
          </div>
        </div>
      </section>

      <section className={styles.audiences} id="peran">
        <div className={styles.sectionIntro}>
          <p className={styles.eyebrow}>Ruang kerja sesuai peran</p>
          <h2>Informasi yang tepat, untuk orang yang tepat.</h2>
        </div>
        <div className={styles.audienceGrid}>
          <article><span>01</span><h3>Peserta</h3><p>Mengetahui target, mengajukan sesi, mengirim video, dan melihat hasil.</p></article>
          <article><span>02</span><h3>Mentor</h3><p>Mendampingi sesi, menilai tema dan video, serta memberi umpan balik.</p></article>
          <article><span>03</span><h3>Dosen</h3><p>Menyiapkan paket, melaksanakan ujian, dan memfinalisasi hasil.</p></article>
          <article><span>04</span><h3>Pengelola</h3><p>Menjaga peserta, penugasan, kalender, dan kebijakan tetap tertata.</p></article>
        </div>
      </section>

      <section className={styles.finalCta}>
        <div className={styles.finalPattern} aria-hidden="true" />
        <div>
          <p className={styles.eyebrow}>Mulai dari langkah hari ini</p>
          <h2>Perjalanan yang baik dimulai dengan arah yang jelas.</h2>
          <p>Masuk untuk melihat target dan pekerjaan terdekat Anda di YAQin.</p>
          <Link className={styles.primaryCtaLight} href="/login">
            Masuk ke ruang kerja <ArrowIcon />
          </Link>
        </div>
      </section>

      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerBrand}>
            <span className={styles.brandMark}>YQ</span>
            <div><strong>YAQin</strong><p>Pendampingan hafalan Juz 30 yang terarah dan dapat ditelusuri.</p></div>
          </div>
          <div className={styles.footerLinks}>
            <a href="#perjalanan">Perjalanan</a><a href="#fitur">Fitur</a><Link href="/login">Masuk</Link>
          </div>
          <p className={styles.copyright}>© 2026 YAQin</p>
        </div>
      </footer>
    </main>
  );
}
