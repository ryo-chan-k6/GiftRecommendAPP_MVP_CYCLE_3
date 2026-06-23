import type { Metadata } from "next";

import { notoSerifJp, shipporiMincho } from "@/lib/fonts";

import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "OKURI 贈",
  description: "Gift Recommendation Service MVP — web-foundation 骨格",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="ja"
      className={`${notoSerifJp.variable} ${shipporiMincho.variable}`}
    >
      <body className="min-h-screen bg-bg font-body text-text antialiased">
        {children}
      </body>
    </html>
  );
}
