import type { StatusTone } from "@/components/ui";

export type SessionStatus =
  "proposed" | "scheduled" | "in_progress" | "completed" | "no_show" | "cancelled";

export type SessionMethod = "in_person" | "video_call";

export type Session = {
  id: string;
  participant: {
    enrollment_id: string;
    user_id: string;
    display_name: string;
    nim: string;
  };
  part_id: string;
  mentor: { user_id: string; display_name: string };
  proposed_at: string;
  scheduled_at: string | null;
  actual_at: string | null;
  method: SessionMethod;
  status: SessionStatus;
  participant_note: string | null;
  mentor_note: string | null;
  row_version: number;
  created_at: string;
  themes: Array<{
    id: string;
    theme_id: string;
    code: string;
    name: string;
    part_id: string;
    part_no: number;
    part_name: string;
  }>;
  allowed_actions: string[];
};

export type Target = {
  id: string;
  theme: {
    id: string;
    code: string;
    name: string;
    part_id: string;
    part_no: number;
    part_name: string;
  };
  status: "scheduled" | "active" | "completed" | "closed";
  locked_reason: string | null;
  allowed_actions: string[];
};

export type SessionContext = {
  user: { display_name: string };
  active_context: { organization_name: string } | null;
  csrf_token: string;
};

export type CursorPage<T> = {
  items: T[];
  page: { has_more: boolean; next_cursor: string | null };
};

type ApiEnvelope<T> = { data: T; request_id: string; version: number | null };

export class ApiFailure extends Error {
  constructor(
    message: string,
    readonly code?: string,
  ) {
    super(message);
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  const body = (await response.json().catch(() => null)) as
    | ApiEnvelope<T>
    | { code?: string; message?: string; detail?: { code?: string; message?: string } }
    | null;
  if (!response.ok) {
    const detail = body && "detail" in body ? body.detail : undefined;
    throw new ApiFailure(
      detail?.message ??
        (body && "message" in body ? body.message : undefined) ??
        "Permintaan gagal diproses.",
      detail?.code ?? (body && "code" in body ? body.code : undefined),
    );
  }
  return (body as ApiEnvelope<T>).data;
}

export function dateTimeLabel(value: string | null): string {
  if (value === null) return "Belum ditentukan";
  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Jakarta",
  }).format(new Date(value));
}

export const sessionStatusLabel: Record<SessionStatus, string> = {
  proposed: "Diajukan",
  scheduled: "Dijadwalkan",
  in_progress: "Berlangsung",
  completed: "Selesai",
  no_show: "Tidak hadir",
  cancelled: "Dibatalkan",
};

export function sessionStatusTone(status: SessionStatus): StatusTone {
  if (status === "completed") return "success";
  if (status === "in_progress" || status === "scheduled") return "progress";
  if (status === "proposed") return "warning";
  if (status === "no_show" || status === "cancelled") return "danger";
  return "neutral";
}

export function toLocalDateTime(value: string): string {
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}
