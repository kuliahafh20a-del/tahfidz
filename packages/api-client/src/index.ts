import createClient from "openapi-fetch";

import type { paths } from "./schema";

export type { components, operations, paths } from "./schema";

/** Create a typed API client from the FastAPI OpenAPI contract. */
export function createYaqinApiClient(baseUrl: string) {
  return createClient<paths>({ baseUrl });
}
