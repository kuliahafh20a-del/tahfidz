import createClient from "openapi-fetch";

import type { paths } from "./schema";

export type { components, operations, paths } from "./schema";

export type ApiEnvelope<T> = {
  data: T;
  request_id: string;
  version: number | null;
};

export type ApiError = {
  code: string;
  details: Record<string, unknown>;
  field_errors: Record<string, string[]>;
  message: string;
  request_id: string;
};

export class YaqinApiError extends Error {
  readonly code: string;
  readonly details: Record<string, unknown>;
  readonly fieldErrors: Record<string, string[]>;
  readonly requestId: string;

  constructor(error: ApiError) {
    super(error.message);
    this.name = "YaqinApiError";
    this.code = error.code;
    this.details = error.details;
    this.fieldErrors = error.field_errors;
    this.requestId = error.request_id;
  }
}

/** Return envelope data while preserving version and request ID for callers that need them. */
export function unwrapApiEnvelope<T>(envelope: ApiEnvelope<T>): T {
  return envelope.data;
}

/** Turn the shared wire error into one predictable application error. */
export function toYaqinApiError(error: ApiError): YaqinApiError {
  return new YaqinApiError(error);
}

/** Create a typed API client from the FastAPI OpenAPI contract. */
export function createYaqinApiClient(baseUrl: string) {
  return createClient<paths>({ baseUrl });
}
