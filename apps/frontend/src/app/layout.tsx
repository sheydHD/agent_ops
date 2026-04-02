import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentOps Demo",
  description:
    "RAG Chat with Langfuse + Phoenix + OTel observability — 100% local",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">
        <header className="border-b border-gray-200 bg-white">
          <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
            <h1 className="text-lg font-semibold text-gray-900">
              AgentOps Demo
            </h1>
            <div className="flex gap-3 text-sm">
              {process.env.NEXT_PUBLIC_LANGFUSE_URL && (
                <a
                  href={process.env.NEXT_PUBLIC_LANGFUSE_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded bg-blue-50 px-2 py-1 text-blue-700 hover:bg-blue-100"
                >
                  Langfuse ↗
                </a>
              )}
              {process.env.NEXT_PUBLIC_PHOENIX_URL && (
                <a
                  href={process.env.NEXT_PUBLIC_PHOENIX_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded bg-orange-50 px-2 py-1 text-orange-700 hover:bg-orange-100"
                >
                  Phoenix ↗
                </a>
              )}
            </div>
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
