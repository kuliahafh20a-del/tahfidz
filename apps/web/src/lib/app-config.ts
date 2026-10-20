export const appConfig = Object.freeze({
  description: "Aplikasi pendampingan hafalan Juz 30",
  name: process.env.NEXT_PUBLIC_APP_NAME ?? "YAQin",
});

export function buildPageTitle(page?: string): string {
  return page ? `${page} | ${appConfig.name}` : appConfig.name;
}
