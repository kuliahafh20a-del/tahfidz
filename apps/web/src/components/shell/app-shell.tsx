"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useState } from "react";

import { roleLabels, roleNavigation, shouldShowRoleSwitcher, type UserRole } from "./navigation";
import styles from "./shell.module.css";

type AppShellProps = Readonly<{
  accountName: string;
  availableRoles?: readonly UserRole[];
  children: ReactNode;
  initialRole: UserRole;
  organization: string;
}>;

export function AppShell({
  accountName,
  availableRoles,
  children,
  initialRole,
  organization,
}: AppShellProps) {
  const pathname = usePathname();
  const roles = availableRoles ?? [initialRole];
  const [activeRole, setActiveRole] = useState(initialRole);
  const [navigationOpen, setNavigationOpen] = useState(false);

  return (
    <div className={styles.appShell}>
      <a className={styles.skipLink} href="#main-content">
        Lewati ke konten utama
      </a>
      <header className={styles.header}>
        <div className={styles.brandGroup}>
          <button
            aria-controls="role-navigation"
            aria-expanded={navigationOpen}
            aria-label={navigationOpen ? "Tutup navigasi" : "Buka navigasi"}
            className={styles.menuButton}
            onClick={() => setNavigationOpen((open) => !open)}
            type="button"
          >
            <span aria-hidden="true">☰</span>
          </button>
          <Link className={styles.brand} href="/">
            <span aria-hidden="true" className={styles.brandMark}>
              YQ
            </span>
            <span>YAQin</span>
          </Link>
          <span className={styles.organization}>{organization}</span>
        </div>

        <div className={styles.accountGroup}>
          {shouldShowRoleSwitcher(roles) ? (
            <label className={styles.roleSwitcher}>
              <span>Peran aktif</span>
              <select
                onChange={(event) => setActiveRole(event.target.value as UserRole)}
                value={activeRole}
              >
                {roles.map((role) => (
                  <option key={role} value={role}>
                    {roleLabels[role]}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <span className={styles.singleRole}>{roleLabels[activeRole]}</span>
          )}
          <span className={styles.account} title={accountName}>
            <span aria-hidden="true" className={styles.avatar}>
              {accountName.slice(0, 1).toUpperCase()}
            </span>
            <span className={styles.accountName}>{accountName}</span>
          </span>
        </div>
      </header>

      <div className={styles.body}>
        <aside
          className={`${styles.sidebar} ${navigationOpen ? styles.sidebarOpen : ""}`}
          id="role-navigation"
        >
          <div className={styles.roleHeading}>
            <span>Ruang kerja</span>
            <strong>{roleLabels[activeRole]}</strong>
          </div>
          <nav aria-label={`Navigasi ${roleLabels[activeRole]}`}>
            <ul className={styles.navigationList}>
              {roleNavigation[activeRole].map((item) => {
                const current = pathname === item.href;
                return (
                  <li key={item.code}>
                    <Link
                      aria-current={current ? "page" : undefined}
                      className={`${styles.navigationLink} ${current ? styles.navigationLinkActive : ""}`}
                      href={item.href}
                      onClick={() => setNavigationOpen(false)}
                    >
                      <span className={styles.navigationCode}>{item.code}</span>
                      <span>{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
          <Link className={styles.homeLink} href="/">
            Kembali ke beranda peran
          </Link>
        </aside>

        {navigationOpen ? (
          <button
            aria-label="Tutup navigasi"
            className={styles.backdrop}
            onClick={() => setNavigationOpen(false)}
            type="button"
          />
        ) : null}

        <div className={styles.contentFrame}>
          <main className={styles.main} id="main-content" tabIndex={-1}>
            {children}
          </main>
          <div
            aria-atomic="true"
            aria-live="polite"
            className="visually-hidden"
            id="system-status"
          />
        </div>
      </div>
    </div>
  );
}
