import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "../lib/auth/AuthContext";

export const metadata: Metadata = {
  title: "Goddess AI 2.0 - Creator Dashboard",
  description: "High-Performance Multi-Stream YouTube Moderation & AI Co-Host Platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#090d16] text-slate-100 min-h-screen antialiased flex flex-col">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
