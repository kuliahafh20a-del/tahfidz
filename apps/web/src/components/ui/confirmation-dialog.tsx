"use client";

import type { ReactNode } from "react";
import { useEffect, useRef } from "react";

import { Button } from "./index";
import styles from "./ui.module.css";

export function ConfirmationDialog({
  children,
  confirmLabel,
  onConfirm,
  onOpenChange,
  open,
  title,
}: Readonly<{
  children: ReactNode;
  confirmLabel: string;
  onConfirm: () => void;
  onOpenChange: (open: boolean) => void;
  open: boolean;
  title: string;
}>) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open && !dialog.open) {
      triggerRef.current = document.activeElement as HTMLElement | null;
      dialog.showModal();
      dialog.querySelector<HTMLElement>("[data-dialog-title]")?.focus();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  function close(): void {
    onOpenChange(false);
    queueMicrotask(() => triggerRef.current?.focus());
  }

  return (
    <dialog
      aria-labelledby="confirmation-dialog-title"
      className={styles.dialog}
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
      onClose={() => {
        if (open) onOpenChange(false);
      }}
      ref={dialogRef}
    >
      <div className={styles.dialogContent}>
        <h2 data-dialog-title id="confirmation-dialog-title" tabIndex={-1}>
          {title}
        </h2>
        <div className={styles.dialogBody}>{children}</div>
        <div className={styles.dialogActions}>
          <Button onClick={close} type="button" variant="secondary">
            Kembali dan periksa
          </Button>
          <Button
            onClick={() => {
              onConfirm();
              close();
            }}
            type="button"
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </dialog>
  );
}
