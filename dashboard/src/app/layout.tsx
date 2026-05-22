import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Shell } from "@/components/layout/shell";
import { ThemeProvider } from "@/contexts/theme-context";
import { LoadingScreen } from "@/components/ui/loading-screen";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AutoReg Dashboard",
  description: "Automated registration platform monitoring dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} dark`}
    >
      <body>
        <ThemeProvider>
          <LoadingScreen />
          <Shell>{children}</Shell>
        </ThemeProvider>
      </body>
    </html>
  );
}
