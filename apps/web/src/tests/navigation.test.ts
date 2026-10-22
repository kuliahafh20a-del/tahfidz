import { describe, expect, it } from "vitest";

import { roleLabels, roleNavigation, shouldShowRoleSwitcher } from "../components/shell/navigation";

describe("role navigation", () => {
  it("provides task navigation for every supported role", () => {
    expect(Object.keys(roleNavigation)).toEqual(Object.keys(roleLabels));
    expect(roleNavigation.participant).toHaveLength(6);
    expect(roleNavigation.mentor).toHaveLength(5);
    expect(roleNavigation.lecturer).toHaveLength(4);
    expect(roleNavigation.department_admin).toHaveLength(3);
    expect(roleNavigation.faculty_admin).toHaveLength(1);
  });

  it("uses unique screen codes and absolute application routes", () => {
    const items = Object.values(roleNavigation).flat();
    expect(new Set(items.map((item) => item.code)).size).toBe(items.length);
    expect(items.every((item) => item.href.startsWith("/"))).toBe(true);
  });

  it("only shows the role switcher for multiple active roles", () => {
    expect(shouldShowRoleSwitcher(["participant"])).toBe(false);
    expect(shouldShowRoleSwitcher(["participant", "participant"])).toBe(false);
    expect(shouldShowRoleSwitcher(["participant", "mentor"])).toBe(true);
  });
});
