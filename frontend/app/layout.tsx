import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Ask My Docs — Production RAG",
  description:
    "Ask questions across your documents with hybrid BM25 + vector retrieval, cross-encoder reranking, and citation-grounded answers.",
  keywords: ["RAG", "AI", "document search", "retrieval augmented generation"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
