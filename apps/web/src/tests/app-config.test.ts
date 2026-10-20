import { describe, expect, it } from "vitest";

import { buildPageTitle } from "../lib/app-config";

describe("buildPageTitle", () => {
  it("uses the application name for the root page", () => {
    expect(buildPageTitle()).toBe("YAQin");
  });

  it("combines a page name with the application name", () => {
    expect(buildPageTitle("Fondasi")).toBe("Fondasi | YAQin");
  });
});
