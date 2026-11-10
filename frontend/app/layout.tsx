import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Patient Companion — understand your medical documents",
  description:
    "A demo that translates medical documents into kind, plain language and helps you prepare for your next appointment. Not medical advice; not HIPAA compliant.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
