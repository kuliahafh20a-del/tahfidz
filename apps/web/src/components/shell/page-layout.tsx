import Link from "next/link";
import type { ReactNode } from "react";

import styles from "./shell.module.css";

type Breadcrumb = Readonly<{ href?: string; label: string }>;

export function PageHeader({
  breadcrumbs,
  description,
  eyebrow,
  status,
  title,
}: Readonly<{
  breadcrumbs: readonly Breadcrumb[];
  description: string;
  eyebrow?: string;
  status?: ReactNode;
  title: string;
}>) {
  return (
    <header className={styles.pageHeader}>
      <nav aria-label="Breadcrumb">
        <ol className={styles.breadcrumbs}>
          {breadcrumbs.map((item, index) => (
            <li key={`${item.label}-${index}`}>
              {item.href ? <Link href={item.href}>{item.label}</Link> : <span>{item.label}</span>}
            </li>
          ))}
        </ol>
      </nav>
      <div className={styles.pageHeadingRow}>
        <div>
          {eyebrow ? <p className={styles.eyebrow}>{eyebrow}</p> : null}
          <h1>{title}</h1>
          <p className={styles.pageDescription}>{description}</p>
        </div>
        {status ? <div className={styles.pageStatus}>{status}</div> : null}
      </div>
    </header>
  );
}

export function WorkSupportLayout({
  children,
  support,
}: Readonly<{ children: ReactNode; support: ReactNode }>) {
  return (
    <div className={styles.workSupportLayout}>
      <div className={styles.workArea}>{children}</div>
      <aside aria-label="Informasi pendamping" className={styles.supportArea}>
        {support}
      </aside>
    </div>
  );
}

export function SupportPanel({
  children,
  title,
}: Readonly<{ children: ReactNode; title: string }>) {
  return (
    <section className={styles.supportPanel}>
      <h2>{title}</h2>
      {children}
    </section>
  );
}
