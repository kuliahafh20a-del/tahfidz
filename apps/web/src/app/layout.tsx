import type { Metadata } from "next";
import type { ReactNode } from "react";

import { appConfig } from "@/lib/app-config";

import "./globals.css";

export const metadata: Metadata = {
  description: appConfig.description,
  title: {
    default: appConfig.name,
    template: `%s | ${appConfig.name}`,
  },
};

type RootLayoutProps = Readonly<{
  children: ReactNode;
}>;

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  );
}
