import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Expense Review",
  description: "Internal expense case review workspace",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen flex flex-col selection:bg-gray-200`}
      >
        <header className="border-b border-gray-200/60 bg-white">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-12">
              <Link href="/claims" className="flex items-center">
                <span className="font-mono text-[11px] tracking-widest text-gray-900 uppercase font-semibold">
                  Expense / Review
                </span>
              </Link>
              <nav className="flex space-x-6">
                <Link
                  href="/claims"
                  className="font-mono text-[11px] tracking-widest text-gray-500 hover:text-blue-600 uppercase transition-colors"
                >
                  Queue
                </Link>
                <Link
                  href="/claims/new"
                  className="font-mono text-[11px] tracking-widest text-gray-500 hover:text-blue-600 uppercase transition-colors"
                >
                  Submit
                </Link>
              </nav>
            </div>
          </div>
        </header>

        <main className="flex-grow max-w-5xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-16">
          {children}
        </main>
      </body>
    </html>
  );
}
