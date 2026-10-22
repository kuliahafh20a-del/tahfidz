import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  TableHTMLAttributes,
} from "react";
import { useId } from "react";

import styles from "./ui.module.css";

export { ConfirmationDialog } from "./confirmation-dialog";

export type StatusTone = "neutral" | "progress" | "success" | "warning" | "danger" | "locked";

const statusIcons: Record<StatusTone, string> = {
  neutral: "•",
  progress: "↻",
  success: "✓",
  warning: "!",
  danger: "×",
  locked: "—",
};

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "tertiary" | "danger";
}) {
  return <button className={`${styles.button} ${styles[variant]} ${className ?? ""}`} {...props} />;
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`${styles.input} ${className ?? ""}`} {...props} />;
}

export function FormField({
  error,
  help,
  id,
  label,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & {
  error?: string;
  help?: string;
  label: string;
}) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const descriptionId = help || error ? `${inputId}-description` : undefined;

  return (
    <div className={styles.formField}>
      <label htmlFor={inputId}>{label}</label>
      <Input
        aria-describedby={descriptionId}
        aria-invalid={error ? true : undefined}
        id={inputId}
        {...props}
      />
      {help || error ? (
        <p className={error ? styles.fieldError : styles.fieldHelp} id={descriptionId}>
          {error ?? help}
        </p>
      ) : null}
    </div>
  );
}

export function StatusBadge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: StatusTone;
}) {
  return (
    <span className={`${styles.badge} ${styles[`badge-${tone}`]}`}>
      <span aria-hidden="true">{statusIcons[tone]}</span>
      {children}
    </span>
  );
}

export function Card({
  children,
  className,
  title,
}: Readonly<{ children: ReactNode; className?: string; title?: string }>) {
  return (
    <section className={`${styles.card} ${className ?? ""}`}>
      {title ? <h2>{title}</h2> : null}
      {children}
    </section>
  );
}

export function DataTable({
  caption,
  headings,
  rows,
  ...props
}: TableHTMLAttributes<HTMLTableElement> & {
  caption: string;
  headings: readonly string[];
  rows: readonly (readonly ReactNode[])[];
}) {
  return (
    <div className={styles.tableScroll} tabIndex={0}>
      <table className={styles.table} {...props}>
        <caption>{caption}</caption>
        <thead>
          <tr>
            {headings.map((heading) => (
              <th key={heading} scope="col">
                {heading}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) =>
                cellIndex === 0 ? (
                  <th key={cellIndex} scope="row">
                    {cell}
                  </th>
                ) : (
                  <td key={cellIndex}>{cell}</td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function FeedbackState({
  action,
  description,
  title,
  tone = "neutral",
}: Readonly<{
  action?: ReactNode;
  description: string;
  title: string;
  tone?: "neutral" | "loading" | "error" | "locked";
}>) {
  const role = tone === "error" ? "alert" : "status";
  return (
    <section className={`${styles.feedback} ${styles[`feedback-${tone}`]}`} role={role}>
      <strong>{title}</strong>
      <p>{description}</p>
      {action ? <div>{action}</div> : null}
    </section>
  );
}
