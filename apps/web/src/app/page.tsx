const foundations = [
  "Next.js App Router dan TypeScript",
  "FastAPI modular monolith",
  "Workspace bersama untuk kontrak dan UI",
];

export default function HomePage() {
  return (
    <main className="shell">
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">Yakin · Amalin · Mutqin</p>
        <h1 id="page-title">Fondasi YAQin siap dikembangkan</h1>
        <p className="lede">
          Bootstrap repository untuk aplikasi pendampingan hafalan Juz 30 telah aktif. Fitur
          akademik akan dibangun bertahap sesuai dependency roadmap.
        </p>
        <ul className="foundation-list">
          {foundations.map((foundation) => (
            <li key={foundation}>{foundation}</li>
          ))}
        </ul>
        <p className="status" role="status">
          TASK-001 · Project setup
        </p>
      </section>
    </main>
  );
}
